"""Realtime Discord voice session skeleton.

This module is intentionally provider-mockable. Phase 2 defines the lifecycle
boundary used by the Discord gateway without opening any network connection on
its own. Later phases can plug an OpenAI Realtime provider behind the same
``start``/``stop``/``send_audio_frame``/``interrupt`` calls.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet, Optional


DEFAULT_REALTIME_TOOL_NAMES: FrozenSet[str] = frozenset(
    {
        "reminders",
        "web_search",
        "image_generation",
    }
)


async def _maybe_await(value: Any) -> Any:
    """Await ``value`` when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


def _discord_pcm48_stereo_to_openai_pcm24_mono(pcm: bytes) -> bytes:
    """Convert Discord-native 48 kHz stereo s16le PCM to OpenAI 24 kHz mono."""
    if not pcm:
        return b""
    try:
        import numpy as np
    except Exception:
        # Conservative fallback: pass through rather than failing the session.
        return pcm
    samples = np.frombuffer(pcm[: len(pcm) - (len(pcm) % 4)], dtype=np.int16)
    if samples.size < 2:
        return b""
    stereo = samples.reshape(-1, 2).astype(np.int32)
    mono48 = ((stereo[:, 0] + stereo[:, 1]) // 2).astype(np.int16)
    mono24 = mono48[::2]
    return mono24.tobytes()


def _openai_pcm24_mono_to_discord_pcm48_stereo(pcm: bytes) -> bytes:
    """Convert OpenAI 24 kHz mono s16le PCM to Discord 48 kHz stereo."""
    if not pcm:
        return b""
    try:
        import numpy as np
    except Exception:
        return pcm
    mono24 = np.frombuffer(pcm[: len(pcm) - (len(pcm) % 2)], dtype=np.int16)
    if mono24.size == 0:
        return b""
    mono48 = np.repeat(mono24, 2)
    stereo48 = np.repeat(mono48[:, None], 2, axis=1).reshape(-1)
    return stereo48.astype(np.int16).tobytes()


class OpenAIRealtimeProvider:

    """OpenAI Realtime WebSocket provider for Discord realtime voice.

    The provider owns only the OpenAI connection and the outbound PCM stream.
    Discord-specific lifecycle remains in :class:`DiscordRealtimeVoiceSession`
    and the adapter.  Tests inject ``websocket_factory`` so no network is
    required for unit coverage.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gpt-realtime",
        output_stream: Any,
        websocket_factory: Any = None,
        instructions: str = "Eres J.A.R.V.I.S. Responde en español de forma breve y natural.",
        tool_handler: Optional[Callable[[str, dict[str, Any]], Any]] = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.output_stream = output_stream
        self.websocket_factory = websocket_factory
        self.instructions = instructions
        self.tool_handler = tool_handler
        self.websocket: Any = None
        self._receive_task: Optional[asyncio.Task] = None
        self._closed = False

    @property
    def uri(self) -> str:
        return f"wss://api.openai.com/v1/realtime?model={self.model}"

    def _build_tools(self) -> list[dict[str, Any]]:
        try:
            from .realtime_tools import build_openai_realtime_tools
        except ImportError:  # pragma: no cover - direct plugin path import fallback
            from realtime_tools import build_openai_realtime_tools
        return build_openai_realtime_tools()

    async def start(self, session: Any) -> None:
        """Open the realtime websocket and configure the audio session."""
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI Realtime voice")
        if self.websocket is not None:
            return
        factory = self.websocket_factory
        if factory is None:
            import websockets  # noqa: PLC0415 - optional at runtime until realtime is used
            factory = websockets.connect
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        self.websocket = await _maybe_await(
            factory(self.uri, additional_headers=headers)
        )
        await self._send_json(
            {
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "instructions": self.instructions,
                    "audio": {
                        "input": {"format": {"type": "audio/pcm", "rate": 24000}},
                        "output": {"format": {"type": "audio/pcm", "rate": 24000}},
                    },
                    "tools": self._build_tools(),
                    "tool_choice": "auto",
                },
            }
        )
        self._closed = False
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def stop(self, reason: str = "") -> None:
        """Close websocket and output stream once."""
        if self._closed:
            return
        self._closed = True
        task = self._receive_task
        self._receive_task = None
        ws = self.websocket
        self.websocket = None
        if task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if ws is not None and hasattr(ws, "close"):
            await _maybe_await(ws.close())
        closer = getattr(self.output_stream, "close", None)
        if closer is not None:
            await _maybe_await(closer())

    async def send_audio_frame(self, pcm: bytes, *, user_id: Optional[int] = None) -> None:
        """Append one PCM chunk to OpenAI's input audio buffer."""
        if not pcm:
            return
        if self.websocket is None:
            raise RuntimeError("OpenAI Realtime websocket is not connected")
        openai_pcm = _discord_pcm48_stereo_to_openai_pcm24_mono(pcm)
        if not openai_pcm:
            return
        await self._send_json(
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(openai_pcm).decode("ascii"),
            }
        )

    async def interrupt(self) -> None:
        """Cancel the current model response when future barge-in enables it."""
        if self.websocket is None:
            return
        await self._send_json({"type": "response.cancel"})

    async def _send_json(self, payload: dict) -> None:
        if self.websocket is None:
            raise RuntimeError("OpenAI Realtime websocket is not connected")
        await _maybe_await(self.websocket.send(json.dumps(payload)))

    async def _receive_loop(self) -> None:
        try:
            async for raw in self.websocket:
                try:
                    event = json.loads(raw)
                except Exception:
                    continue
                event_type = event.get("type")
                if event_type in {"response.output_audio.delta", "response.audio.delta", "output_audio.delta"}:
                    delta = event.get("delta") or event.get("audio")
                    if not delta:
                        continue
                    try:
                        pcm = base64.b64decode(delta)
                    except Exception:
                        continue
                    discord_pcm = _openai_pcm24_mono_to_discord_pcm48_stereo(pcm)
                    if not discord_pcm:
                        continue
                    writer = getattr(self.output_stream, "write", None)
                    if writer is not None:
                        await _maybe_await(writer(discord_pcm))
                elif event_type == "response.output_item.done":
                    item = event.get("item") or {}
                    if item.get("type") == "function_call":
                        await self._handle_function_call_item(item)
                elif event_type in {"response.function_call_arguments.done", "function_call_arguments.done"}:
                    await self._handle_function_call_item(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            # The adapter/session cleanup path owns user-visible reporting.  The
            # provider should fail closed rather than crash the gateway thread.
            return
    async def _handle_function_call_item(self, item: dict[str, Any]) -> None:
        """Run a safe realtime tool call and return function output to OpenAI."""
        name = str(item.get("name") or "")
        if not name:
            return
        raw_args = item.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except Exception:
            arguments = {}
        handler = self.tool_handler
        if handler is None:
            try:
                from .realtime_tools import dispatch_realtime_tool
            except ImportError:  # pragma: no cover - direct plugin path import fallback
                from realtime_tools import dispatch_realtime_tool
            result = dispatch_realtime_tool(name, arguments)
        else:
            result = await _maybe_await(handler(name, arguments))
        call_id = item.get("call_id") or item.get("id")
        if not call_id or self.websocket is None:
            return
        try:
            await self._send_json(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result or {}, ensure_ascii=False),
                    },
                }
            )
        except Exception:
            return


@dataclass(slots=True)
class DiscordRealtimeVoiceSession:
    """Lifecycle wrapper for one Discord realtime voice session.

    Parameters are deliberately plain data so tests and later adapter code can
    construct the session without Discord.py objects. ``provider`` is any object
    exposing async or sync methods named ``start``, ``stop``,
    ``send_audio_frame``, and optionally ``interrupt``.
    """

    guild_id: int
    voice_channel_id: int
    text_channel_id: int
    source: Any
    provider: Any
    allowed_tool_names: FrozenSet[str] = DEFAULT_REALTIME_TOOL_NAMES
    barge_in_enabled: bool = False
    _active: bool = field(default=False, init=False, repr=False)
    _stopped: bool = field(default=False, init=False, repr=False)

    @property
    def active(self) -> bool:
        """Whether the realtime session is currently active."""
        return self._active

    async def start(self) -> None:
        """Start the provider-backed session.

        Idempotent for safety: repeated calls after a successful start do not
        create a second provider session.
        """
        if self._active:
            return
        starter = getattr(self.provider, "start", None)
        if starter is None:
            raise RuntimeError("Realtime provider does not implement start()")
        await _maybe_await(starter(self))
        self._active = True
        self._stopped = False

    async def stop(self, reason: str = "") -> None:
        """Stop the provider-backed session once.

        Stop is idempotent so cleanup paths may call it repeatedly without
        double-closing sockets or double-sending provider events.
        """
        if not self._active or self._stopped:
            self._active = False
            return
        stopper = getattr(self.provider, "stop", None)
        if stopper is not None:
            await _maybe_await(stopper(reason=reason))
        self._active = False
        self._stopped = True

    async def send_audio_frame(
        self,
        pcm: bytes,
        *,
        user_id: Optional[int] = None,
    ) -> None:
        """Forward one PCM frame/chunk to the provider.

        The audio format contract is defined by later integration phases; this
        skeleton simply enforces lifecycle state and forwards opaque bytes.
        """
        if not self._active:
            raise RuntimeError("Realtime voice session is not active")
        if not pcm:
            return
        sender = getattr(self.provider, "send_audio_frame", None)
        if sender is None:
            raise RuntimeError("Realtime provider does not implement send_audio_frame()")
        await _maybe_await(sender(pcm, user_id=user_id))

    async def interrupt(self) -> None:
        """Placeholder for deferred barge-in support.

        In Phase 2, interrupt is intentionally safe and minimal: it is a no-op
        when inactive and forwards to the provider when active. Actual speech
        detection, response cancellation, and output-buffer clearing belong to
        the later barge-in phase.
        """
        if not self._active:
            return
        interrupter = getattr(self.provider, "interrupt", None)
        if interrupter is not None:
            await _maybe_await(interrupter())
