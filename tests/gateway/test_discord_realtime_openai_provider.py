"""Tests for the OpenAI Realtime provider used by Discord realtime voice.

All tests use a fake websocket: no OpenAI network call and no real Discord
socket. This locks the provider boundary before live integration.
"""

import asyncio
import base64
import json
from types import SimpleNamespace

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import SessionSource


class FakeWebSocket:
    def __init__(self, incoming=None, fail_on_send: int | None = None):
        self.sent = []
        self.incoming = list(incoming or [])
        self.closed = False
        self.fail_on_send = fail_on_send
        self.send_count = 0

    async def send(self, message):
        self.send_count += 1
        if self.fail_on_send is not None and self.send_count == self.fail_on_send:
            raise RuntimeError("simulated send failure")
        self.sent.append(json.loads(message))

    async def close(self):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.incoming:
            raise StopAsyncIteration
        return self.incoming.pop(0)


class FakeStream:
    def __init__(self):
        self.writes = []
        self.closed = False

    def write(self, pcm):
        self.writes.append(pcm)

    def close(self):
        self.closed = True


class WebSocketFactory:
    def __init__(self, websocket):
        self.websocket = websocket
        self.calls = []

    def __call__(self, uri, **kwargs):
        self.calls.append((uri, kwargs))
        return self.websocket


class FakeProvider:
    def __init__(self):
        self.started_with = None
        self.stop_reasons = []
        self.frames = []

    async def start(self, session):
        self.started_with = session

    async def stop(self, reason=""):
        self.stop_reasons.append(reason)

    async def send_audio_frame(self, pcm, *, user_id=None):
        self.frames.append((pcm, user_id))


def _source() -> SessionSource:
    return SessionSource(
        chat_id="123",
        user_id="442796886135537684",
        user_name="Jonatan",
        platform=Platform.DISCORD,
        chat_type="channel",
        chat_name="La Caverna / #jarvis",
    )


def test_openai_provider_start_opens_realtime_websocket_and_configures_session():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    ws = FakeWebSocket()
    factory = WebSocketFactory(ws)
    stream = FakeStream()
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        model="gpt-realtime",
        output_stream=stream,
        websocket_factory=factory,
        instructions="Eres J.A.R.V.I.S. Responde en español.",
    )

    async def run():
        await provider.start(session=object())
        await provider.stop("test")

    asyncio.run(run())

    uri, kwargs = factory.calls[0]
    assert uri == "wss://api.openai.com/v1/realtime?model=gpt-realtime"
    assert kwargs["additional_headers"] == {"Authorization": "Bearer sk-test"}
    assert ws.sent[0]["type"] == "session.update"
    assert ws.sent[0]["session"]["type"] == "realtime"
    assert ws.sent[0]["session"]["instructions"] == "Eres J.A.R.V.I.S. Responde en español."
    assert ws.sent[0]["session"]["audio"]["input"]["format"] == {"type": "audio/pcm", "rate": 24000}
    assert ws.sent[0]["session"]["audio"]["output"]["format"] == {"type": "audio/pcm", "rate": 24000}


def test_openai_provider_session_update_exposes_only_safe_realtime_tools():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    ws = FakeWebSocket()
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=FakeStream(),
        websocket_factory=WebSocketFactory(ws),
    )

    async def run():
        await provider.start(session=object())
        await provider.stop("done")

    asyncio.run(run())

    tools = ws.sent[0]["session"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {
        "create_reminder",
        "web_search_summary",
        "generate_image_to_discord",
        "leave_voice_channel",
    }
    assert "terminal" not in names
    assert "files" not in names
    assert ws.sent[0]["session"]["tool_choice"] == "auto"


def test_openai_provider_start_closes_websocket_when_session_update_fails():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    ws = FakeWebSocket(fail_on_send=1)
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=FakeStream(),
        websocket_factory=WebSocketFactory(ws),
    )

    async def run():
        try:
            await provider.start(session=object())
        except RuntimeError as exc:
            assert "simulated send failure" in str(exc)
        else:
            raise AssertionError("provider.start() should have failed")

    asyncio.run(run())

    assert ws.closed is True
    assert provider.websocket is None
    assert provider._receive_task is None


def test_realtime_tool_dispatch_rejects_non_allowlisted_tools():
    from plugins.platforms.discord.realtime_tools import dispatch_realtime_tool

    result = dispatch_realtime_tool("terminal", {"command": "whoami"})

    assert result["ok"] is False
    assert "modo operativo completo" in result["message"].lower()


def test_realtime_tool_dispatch_accepts_allowed_tool_names_as_pending_stubs():
    from plugins.platforms.discord.realtime_tools import dispatch_realtime_tool

    result = dispatch_realtime_tool("web_search_summary", {"query": "Hermes Agent"})

    assert result["ok"] is True
    assert result["tool"] == "web_search_summary"
    assert "pendiente" in result["message"].lower() or "pending" in result["message"].lower()


def test_realtime_tool_dispatch_accepts_leave_voice_channel():
    from plugins.platforms.discord.realtime_tools import dispatch_realtime_tool

    result = dispatch_realtime_tool("leave_voice_channel", {"reason": "user asked"})

    assert result["ok"] is True
    assert result["tool"] == "leave_voice_channel"
    assert result["arguments"] == {"reason": "user asked"}


def test_openai_provider_send_audio_frame_converts_discord_pcm48_stereo_to_openai_pcm24_mono():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    ws = FakeWebSocket()
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=FakeStream(),
        websocket_factory=WebSocketFactory(ws),
    )
    # Two 48kHz stereo frames worth of samples: L/R pairs averaged, then every
    # second mono sample is retained for 24kHz OpenAI input.
    discord_pcm = b"\x01\x00\x03\x00" + b"\x05\x00\x07\x00"
    expected_openai_pcm24_mono = b"\x02\x00"

    async def run():
        await provider.start(session=object())
        await provider.send_audio_frame(discord_pcm, user_id=42)
        await provider.stop("done")

    asyncio.run(run())

    append = next(message for message in ws.sent if message["type"] == "input_audio_buffer.append")
    assert append["audio"] == base64.b64encode(expected_openai_pcm24_mono).decode("ascii")


def test_openai_provider_decodes_output_audio_delta_into_discord_pcm48_stereo_stream():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    openai_pcm24_mono = b"\x01\x00\x02\x00"
    expected_discord_pcm48_stereo = (
        b"\x01\x00\x01\x00"
        b"\x01\x00\x01\x00"
        b"\x02\x00\x02\x00"
        b"\x02\x00\x02\x00"
    )
    ws = FakeWebSocket([
        json.dumps({
            "type": "response.output_audio.delta",
            "delta": base64.b64encode(openai_pcm24_mono).decode("ascii"),
        })
    ])
    stream = FakeStream()
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=stream,
        websocket_factory=WebSocketFactory(ws),
    )

    async def run():
        await provider.start(session=object())
        await asyncio.sleep(0)
        await provider.stop("done")

    asyncio.run(run())

    assert stream.writes == [expected_discord_pcm48_stereo]


def test_openai_provider_dispatches_leave_voice_channel_tool_call():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    calls = []
    ws = FakeWebSocket([
        json.dumps({
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "call_id": "call_leave_1",
                "name": "leave_voice_channel",
                "arguments": json.dumps({"reason": "user asked"}),
            },
        })
    ])

    async def tool_handler(name, arguments):
        calls.append((name, arguments))
        return {"ok": True, "message": "leaving"}

    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=FakeStream(),
        websocket_factory=WebSocketFactory(ws),
        tool_handler=tool_handler,
    )

    async def run():
        await provider.start(session=object())
        await asyncio.sleep(0)
        await provider.stop("done")

    asyncio.run(run())

    assert calls == [("leave_voice_channel", {"reason": "user asked"})]
    assert any(message.get("type") == "conversation.item.create" for message in ws.sent)


def test_openai_provider_stop_closes_websocket_and_output_stream_once():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    ws = FakeWebSocket()
    stream = FakeStream()
    provider = OpenAIRealtimeProvider(
        api_key="sk-test",
        output_stream=stream,
        websocket_factory=WebSocketFactory(ws),
    )

    async def run():
        await provider.start(session=object())
        await provider.stop("leave")
        await provider.stop("second")

    asyncio.run(run())

    assert ws.closed is True
    assert stream.closed is True


def test_openai_provider_rejects_missing_api_key_before_opening_websocket():
    from plugins.platforms.discord.realtime_voice import OpenAIRealtimeProvider

    factory = WebSocketFactory(FakeWebSocket())
    provider = OpenAIRealtimeProvider(
        api_key="",
        output_stream=FakeStream(),
        websocket_factory=factory,
    )

    async def run():
        try:
            await provider.start(session=object())
        except RuntimeError as exc:
            return str(exc)
        raise AssertionError("start should fail")

    message = asyncio.run(run())

    assert "OPENAI_API_KEY" in message
    assert factory.calls == []


def test_discord_adapter_starts_realtime_session_with_mixer_stream_and_provider():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={"voice_realtime": {"model": "gpt-realtime"}})
    adapter._voice_mixers = {}
    adapter._realtime_voice_sessions = {}
    stream = FakeStream()
    stream_calls = []

    def create_stream(*args, **kwargs):
        stream_calls.append((args, kwargs))
        return stream

    mixer = SimpleNamespace(create_pcm_stream=create_stream)
    adapter._voice_mixers[999] = mixer
    provider = FakeProvider()

    async def run():
        session = await adapter.start_realtime_voice_session(
            guild_id=999,
            voice_channel=SimpleNamespace(id=555),
            source=_source(),
            provider_factory=lambda **kwargs: provider,
        )
        await adapter.stop_realtime_voice_session(999)
        return session

    session = asyncio.run(run())

    assert session.guild_id == 999
    assert session.voice_channel_id == 555
    assert session.text_channel_id == 123
    assert provider.started_with is session
    assert provider.stop_reasons == ["leave"]
    assert adapter._realtime_voice_sessions == {}
    assert stream_calls[0][1]["max_frames"] >= 500


def test_realtime_output_stream_large_burst_does_not_drop_normal_response_audio():
    from plugins.platforms.discord import voice_mixer as vm

    stream = vm.StreamingPCMChild("openai-realtime", max_frames=600, fade_in_ms=0)
    for value in range(250):  # 5 seconds at 20 ms/frame, commonly delivered faster than realtime.
        frame = (b"\x01\x00" * (vm.SAMPLES_PER_FRAME * vm.CHANNELS))
        stream.write(frame)

    assert stream.dropped_frames == 0


def test_discord_adapter_starts_realtime_session_by_installing_required_mixer_when_voice_fx_disabled():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={})
    adapter._voice_mixers = {}
    adapter._realtime_voice_sessions = {}
    adapter._voice_receivers = {}
    adapter._allowed_user_ids = set()
    adapter._voice_clients = {999: SimpleNamespace(is_connected=lambda: True)}
    adapter._voice_fx_cfg = {"enabled": False}
    stream = FakeStream()
    installed = []

    async def install_mixer(guild_id, vc, *, ambient_enabled=None):
        installed.append((guild_id, vc, ambient_enabled))
        adapter._voice_mixers[guild_id] = SimpleNamespace(create_pcm_stream=lambda *args, **kwargs: stream)

    adapter._install_voice_mixer = install_mixer
    provider = FakeProvider()

    async def run():
        session = await adapter.start_realtime_voice_session(
            guild_id=999,
            voice_channel=SimpleNamespace(id=555),
            source=_source(),
            provider_factory=lambda **kwargs: provider,
        )
        await adapter.stop_realtime_voice_session(999)
        return session

    session = asyncio.run(run())

    assert session.guild_id == 999
    assert installed == [(999, adapter._voice_clients[999], False)]
    assert provider.started_with is session


def test_discord_adapter_rejects_realtime_start_without_connected_voice_client_or_mixer():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={})
    adapter._voice_mixers = {}
    adapter._realtime_voice_sessions = {}
    adapter._voice_clients = {}

    async def run():
        try:
            await adapter.start_realtime_voice_session(
                guild_id=999,
                voice_channel=SimpleNamespace(id=555),
                source=_source(),
                provider_factory=lambda **kwargs: FakeProvider(),
            )
        except RuntimeError as exc:
            return str(exc)
        raise AssertionError("start should fail")

    message = asyncio.run(run())

    assert "connected Discord voice client" in message


class FakeReceiver:
    def __init__(self):
        self.callback = None
        self.stopped = False

    def set_realtime_pcm_callback(self, callback):
        self.callback = callback

    def stop(self):
        self.stopped = True


class FakeVoiceClient:
    def __init__(self, connected=True):
        self.connected = connected
        self.disconnected = False
        self.stopped = False

    def is_connected(self):
        return self.connected

    def is_playing(self):
        return False

    def stop(self):
        self.stopped = True

    async def disconnect(self):
        self.disconnected = True
        self.connected = False


class RecordingProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.frame_event = None

    async def send_audio_frame(self, pcm, *, user_id=None):
        await super().send_audio_frame(pcm, user_id=user_id)
        if self.frame_event:
            self.frame_event.set()


def test_discord_adapter_realtime_receiver_callback_forwards_pcm_to_session():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={})
    adapter._voice_mixers = {}
    adapter._voice_receivers = {}
    adapter._realtime_voice_sessions = {}
    adapter._allowed_user_ids = set()
    stream = FakeStream()
    adapter._voice_mixers[999] = SimpleNamespace(create_pcm_stream=lambda *args, **kwargs: stream)
    receiver = FakeReceiver()
    adapter._voice_receivers[999] = receiver
    provider = RecordingProvider()

    async def run():
        provider.frame_event = asyncio.Event()
        await adapter.start_realtime_voice_session(
            guild_id=999,
            voice_channel=SimpleNamespace(id=555),
            source=_source(),
            provider_factory=lambda **kwargs: provider,
        )
        assert receiver.callback is not None
        receiver.callback(user_id=42, pcm=b"live-pcm")
        await asyncio.wait_for(provider.frame_event.wait(), timeout=1)
        await adapter.stop_realtime_voice_session(999)

    asyncio.run(run())

    assert provider.frames == [(b"live-pcm", 42)]


def test_discord_adapter_stop_realtime_session_clears_receiver_callback():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={})
    adapter._voice_mixers = {999: SimpleNamespace(create_pcm_stream=lambda *args, **kwargs: FakeStream())}
    adapter._voice_receivers = {999: FakeReceiver()}
    adapter._realtime_voice_sessions = {}
    adapter._allowed_user_ids = set()
    provider = FakeProvider()

    async def run():
        await adapter.start_realtime_voice_session(
            guild_id=999,
            voice_channel=SimpleNamespace(id=555),
            source=_source(),
            provider_factory=lambda **kwargs: provider,
        )
        assert adapter._voice_receivers[999].callback is not None
        await adapter.stop_realtime_voice_session(999)

    asyncio.run(run())

    assert adapter._voice_receivers[999].callback is None


def test_discord_adapter_realtime_leave_tool_disconnects_voice_channel_and_is_idempotent():
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter.config = PlatformConfig(enabled=True, extra={})
    adapter._voice_locks = {}
    adapter._voice_clients = {999: FakeVoiceClient()}
    adapter._voice_receivers = {999: FakeReceiver()}
    adapter._voice_listen_tasks = {}
    adapter._voice_mixers = {999: SimpleNamespace(create_pcm_stream=lambda *args, **kwargs: FakeStream())}
    adapter._voice_timeout_tasks = {}
    adapter._voice_text_channels = {999: object()}
    adapter._voice_sources = {999: object()}
    adapter._realtime_voice_sessions = {}
    adapter._allowed_user_ids = set()
    provider = FakeProvider()

    async def run():
        await adapter.start_realtime_voice_session(
            guild_id=999,
            voice_channel=SimpleNamespace(id=555),
            source=_source(),
            provider_factory=lambda **kwargs: provider,
        )
        vc = adapter._voice_clients[999]
        first = await adapter.handle_realtime_tool(999, "leave_voice_channel", {"reason": "user asked"})
        second = await adapter.handle_realtime_tool(999, "leave_voice_channel", {})
        return vc, first, second

    vc, first, second = asyncio.run(run())

    assert first["ok"] is True
    assert first["tool"] == "leave_voice_channel"
    assert second["ok"] is True
    assert vc.disconnected is True
    assert provider.stop_reasons == ["leave"]
    assert adapter._voice_clients == {}
    assert adapter._realtime_voice_sessions == {}
