"""Tests for the Discord realtime voice session skeleton.

Phase 2 keeps this provider-mockable: no Discord socket, no OpenAI network, and
no real audio pipeline yet.
"""

import asyncio
from types import SimpleNamespace

import pytest

from gateway.config import Platform
from gateway.platforms.base import SessionSource


def _source() -> SessionSource:
    return SessionSource(
        chat_id="123",
        user_id="442796886135537684",
        user_name="Jonatan",
        platform=Platform.DISCORD,
        chat_type="channel",
        chat_name="La Caverna / #jarvis",
    )


class FakeRealtimeProvider:
    def __init__(self):
        self.started_with = None
        self.stop_reasons = []
        self.frames = []
        self.interrupt_count = 0

    async def start(self, session):
        self.started_with = session

    async def stop(self, reason=""):
        self.stop_reasons.append(reason)

    async def send_audio_frame(self, pcm, *, user_id=None):
        self.frames.append((pcm, user_id))

    async def interrupt(self):
        self.interrupt_count += 1


class TestDiscordRealtimeVoiceSessionPhase2:
    def test_start_sets_active_and_calls_provider_with_session(self):
        from plugins.platforms.discord.realtime_voice import DiscordRealtimeVoiceSession

        provider = FakeRealtimeProvider()
        session = DiscordRealtimeVoiceSession(
            guild_id=999,
            voice_channel_id=555,
            text_channel_id=123,
            source=_source(),
            provider=provider,
        )

        asyncio.run(session.start())

        assert session.active is True
        assert provider.started_with is session
        assert session.guild_id == 999
        assert session.voice_channel_id == 555
        assert session.text_channel_id == 123

    def test_stop_is_idempotent_and_marks_inactive(self):
        from plugins.platforms.discord.realtime_voice import DiscordRealtimeVoiceSession

        provider = FakeRealtimeProvider()
        session = DiscordRealtimeVoiceSession(
            guild_id=999,
            voice_channel_id=555,
            text_channel_id=123,
            source=_source(),
            provider=provider,
        )

        asyncio.run(session.start())
        asyncio.run(session.stop("leave"))
        asyncio.run(session.stop("second-call"))

        assert session.active is False
        assert provider.stop_reasons == ["leave"]

    def test_send_audio_frame_requires_active_session_and_forwards_user_id(self):
        from plugins.platforms.discord.realtime_voice import DiscordRealtimeVoiceSession

        provider = FakeRealtimeProvider()
        session = DiscordRealtimeVoiceSession(
            guild_id=999,
            voice_channel_id=555,
            text_channel_id=123,
            source=_source(),
            provider=provider,
        )

        with pytest.raises(RuntimeError, match="not active"):
            asyncio.run(session.send_audio_frame(b"pcm", user_id=42))

        asyncio.run(session.start())
        asyncio.run(session.send_audio_frame(b"pcm", user_id=42))

        assert provider.frames == [(b"pcm", 42)]

    def test_interrupt_is_safe_placeholder_for_deferred_barge_in(self):
        from plugins.platforms.discord.realtime_voice import DiscordRealtimeVoiceSession

        provider = FakeRealtimeProvider()
        session = DiscordRealtimeVoiceSession(
            guild_id=999,
            voice_channel_id=555,
            text_channel_id=123,
            source=_source(),
            provider=provider,
        )

        # Inactive interrupt is a no-op so cleanup paths can call it safely.
        asyncio.run(session.interrupt())
        assert provider.interrupt_count == 0

        asyncio.run(session.start())
        asyncio.run(session.interrupt())

        assert provider.interrupt_count == 1
        assert session.barge_in_enabled is False

    def test_allowed_tool_names_are_limited_to_realtime_mvp_scope(self):
        from plugins.platforms.discord.realtime_voice import DiscordRealtimeVoiceSession

        session = DiscordRealtimeVoiceSession(
            guild_id=999,
            voice_channel_id=555,
            text_channel_id=123,
            source=_source(),
            provider=FakeRealtimeProvider(),
        )

        assert session.allowed_tool_names == frozenset({
            "reminders",
            "web_search",
            "image_generation",
        })
        assert "terminal" not in session.allowed_tool_names
        assert "files" not in session.allowed_tool_names
