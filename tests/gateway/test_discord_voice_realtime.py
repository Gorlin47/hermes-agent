"""Tests for Discord /voice realtime command routing.

Phase 1 deliberately covers command/state behavior only. Real audio streaming,
OpenAI Realtime, tools, and barge-in are later phases.
"""

import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType, SessionSource


def _make_discord_event(text: str = "/voice realtime", chat_id: str = "123", guild_id: int = 999) -> MessageEvent:
    source = SessionSource(
        chat_id=chat_id,
        user_id="442796886135537684",
        user_name="Jonatan",
        platform=Platform.DISCORD,
        chat_type="channel",
        chat_name="La Caverna / #jarvis",
    )
    source.thread_id = None
    event = MessageEvent(text=text, message_type=MessageType.TEXT, source=source)
    event.message_id = "msg-realtime"
    event.raw_message = SimpleNamespace(guild_id=guild_id, guild=None)
    return event


def _make_runner(tmp_path):
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner._voice_mode = {}
    runner._VOICE_MODE_PATH = tmp_path / "gateway_voice_mode.json"
    runner._session_db = None
    runner.session_store = MagicMock()
    runner._is_user_authorized = lambda source: True
    return runner


class TestDiscordVoiceRealtimeCommandPhase1:
    @pytest.fixture
    def runner(self, tmp_path):
        return _make_runner(tmp_path)

    def test_discord_native_voice_slash_choices_include_realtime_mode(self):
        from plugins.platforms.discord.adapter import DiscordAdapter

        source = inspect.getsource(DiscordAdapter._register_slash_commands)

        assert 'Voice mode: join, realtime, channel, leave, on, tts, off, or status' in source
        assert 'Choice(name="realtime — realtime streaming voice", value="realtime")' in source

    def test_voice_realtime_dispatches_to_realtime_join_handler(self, runner):
        event = _make_discord_event("/voice realtime")
        runner._handle_voice_realtime_join = AsyncMock(return_value="Realtime voice active in General.")

        result = asyncio.run(runner._handle_voice_command(event))

        runner._handle_voice_realtime_join.assert_awaited_once_with(event)
        assert "realtime" in result.lower()

    def test_voice_join_still_dispatches_to_turn_based_join_handler(self, runner):
        event = _make_discord_event("/voice join")
        runner._handle_voice_channel_join = AsyncMock(return_value="Joined voice channel **General**.")
        runner._handle_voice_realtime_join = AsyncMock(return_value="should not happen")

        result = asyncio.run(runner._handle_voice_command(event))

        runner._handle_voice_channel_join.assert_awaited_once_with(event)
        runner._handle_voice_realtime_join.assert_not_awaited()
        assert "joined" in result.lower()

    def test_voice_join_realtime_is_rejected_not_treated_as_toggle_or_join(self, runner):
        event = _make_discord_event("/voice join realtime")
        runner._handle_voice_channel_join = AsyncMock(return_value="should not happen")
        runner._handle_voice_realtime_join = AsyncMock(return_value="should not happen")

        result = asyncio.run(runner._handle_voice_command(event))

        runner._handle_voice_channel_join.assert_not_awaited()
        runner._handle_voice_realtime_join.assert_not_awaited()
        assert "unsupported" in result.lower() or "not supported" in result.lower()
        assert "voice:123" not in runner._voice_mode

    def test_voice_realtime_status_reports_limited_tools_and_barge_in_deferred(self, runner):
        event = _make_discord_event("/voice status")
        runner._voice_mode["discord:123"] = "realtime"
        adapter = SimpleNamespace(
            get_voice_channel_info=lambda guild_id: {
                "channel_name": "General",
                "member_count": 2,
                "members": [],
            }
        )
        runner.adapters[Platform.DISCORD] = adapter

        result = asyncio.run(runner._handle_voice_command(event))
        lowered = result.lower()

        assert "realtime" in lowered
        assert "general" in lowered
        assert "reminders" in lowered
        assert "web_search" in lowered
        assert "image_generation" in lowered
        assert "barge-in" in lowered
        assert "deferred" in lowered or "pending" in lowered

    def test_voice_realtime_start_failure_does_not_mark_realtime_mode(self, runner):
        event = _make_discord_event("/voice realtime")
        voice_channel = SimpleNamespace(id=555, name="General")
        adapter = SimpleNamespace(
            get_user_voice_channel=AsyncMock(return_value=voice_channel),
            join_voice_channel=AsyncMock(return_value=True),
            start_realtime_voice_session=AsyncMock(side_effect=RuntimeError("VoiceMixer exploded")),
            leave_voice_channel=AsyncMock(),
            _voice_text_channels={},
            _voice_sources={},
            _voice_input_callback=object(),
            _on_voice_disconnect=None,
        )
        runner.adapters[Platform.DISCORD] = adapter
        runner._set_adapter_auto_tts_enabled = MagicMock()
        runner._save_voice_modes = MagicMock()
        runner._handle_voice_timeout_cleanup = AsyncMock()

        result = asyncio.run(runner._handle_voice_realtime_join(event))

        assert "could not start realtime" in result.lower() or "no pude iniciar realtime" in result.lower()
        assert "discord:123" not in runner._voice_mode
        runner._save_voice_modes.assert_not_called()
        adapter.leave_voice_channel.assert_awaited_once_with(999)

    def test_voice_leave_stops_realtime_session_before_leaving_channel(self, runner):
        event = _make_discord_event("/voice leave")
        runner._voice_mode["discord:123"] = "realtime"
        adapter = SimpleNamespace(
            is_in_voice_channel=MagicMock(return_value=True),
            stop_realtime_voice_session=AsyncMock(return_value=True),
            leave_voice_channel=AsyncMock(),
            _voice_input_callback=object(),
            _auto_tts_disabled_chats=set(),
            _auto_tts_enabled_chats=set(),
        )
        runner.adapters[Platform.DISCORD] = adapter

        result = asyncio.run(runner._handle_voice_command(event))

        adapter.stop_realtime_voice_session.assert_awaited_once_with(999)
        adapter.leave_voice_channel.assert_awaited_once_with(999)
        assert runner._voice_mode["discord:123"] == "off"
        assert "left" in result.lower()
