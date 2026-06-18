"""Tests for the /jarvis gateway command.

Covers the new direct-mode state toggle, policy rendering, and prompt
passthrough semantics that keep /jarvis <prompt> from getting eaten as a
terminal slash command.
"""

from __future__ import annotations

import asyncio

from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource


def _make_event(text: str = "/jarvis", *, chat_id: str = "67890") -> MessageEvent:
    source = SessionSource(
        platform=Platform.TELEGRAM,
        user_id="12345",
        chat_id=chat_id,
        user_name="testuser",
    )
    return MessageEvent(text=text, source=source)


def _make_runner():
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner._jarvis_direct_mode_sessions = {}
    return runner


class TestJarvisGatewayCommand:
    def test_status_reports_off_by_default(self):
        runner = _make_runner()
        event = _make_event("/jarvis status")

        result = asyncio.run(runner._handle_jarvis_command(event, "session-1"))

        assert "Jarvis direct mode: OFF" in result
        assert "delegation disabled" in result

    def test_policy_shows_worker_map(self):
        runner = _make_runner()
        event = _make_event("/jarvis policy")

        result = asyncio.run(runner._handle_jarvis_command(event, "session-1"))

        assert "Jarvis worker routing:" in result
        assert "Scout" in result
        assert "Reviewer" in result
        assert "Escalation rules:" in result

    def test_on_sets_direct_mode_state(self):
        runner = _make_runner()
        event = _make_event("/jarvis on")

        result = asyncio.run(runner._handle_jarvis_command(event, "session-1"))

        assert "enabled" in result.lower()
        assert runner._jarvis_direct_mode_sessions.get("session-1") is True

    def test_off_clears_direct_mode_state(self):
        runner = _make_runner()
        runner._jarvis_direct_mode_sessions["session-1"] = True
        event = _make_event("/jarvis off")

        result = asyncio.run(runner._handle_jarvis_command(event, "session-1"))

        assert "disabled" in result.lower()
        assert "session-1" not in runner._jarvis_direct_mode_sessions

    def test_prompt_rewrites_text_and_falls_through(self):
        runner = _make_runner()
        event = _make_event("/jarvis build the routing map")

        result = asyncio.run(runner._handle_jarvis_command(event, "session-1"))

        assert result is None
        assert event.text == "build the routing map"
        assert runner._jarvis_direct_mode_sessions.get("session-1") is True

    def test_agent_signature_changes_with_direct_mode(self):
        from gateway.run import GatewayRunner

        sig_off = GatewayRunner._agent_config_signature(
            "model-a",
            {"provider": "openai", "api_key": "x"},
            ["tools"],
            "prompt",
            jarvis_direct_mode=False,
        )
        sig_on = GatewayRunner._agent_config_signature(
            "model-a",
            {"provider": "openai", "api_key": "x"},
            ["tools"],
            "prompt",
            jarvis_direct_mode=True,
        )

        assert sig_off != sig_on

    def test_disabled_toolsets_include_delegation_when_enabled(self):
        runner = _make_runner()
        runner._jarvis_direct_mode_sessions["session-1"] = True

        result = runner._resolve_session_disabled_toolsets(
            {"disabled_toolsets": ["memory"]},
            "session-1",
        )

        assert result == ["delegation", "memory"]
