"""Tests for Telegram voice-note reply length gating."""

from gateway.config import GatewayConfig, Platform
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource


def _make_runner(limit_seconds: int = 30) -> GatewayRunner:
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.config = GatewayConfig(voice_reply_max_seconds=limit_seconds)
    runner._voice_mode = {f"telegram:123": "voice_only"}
    runner.adapters = {}
    return runner


def _make_event() -> MessageEvent:
    return MessageEvent(
        text="",
        message_type=MessageType.VOICE,
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="123", chat_type="dm"),
        message_id="m1",
    )


def test_telegram_voice_reply_uses_voice_for_short_answers():
    runner = _make_runner(limit_seconds=30)
    event = _make_event()

    assert runner._should_send_voice_reply(
        event,
        "uno dos tres cuatro cinco seis siete ocho nueve diez",
        agent_messages=[],
        already_sent=False,
    ) is True


def test_telegram_voice_reply_stays_text_for_long_answers():
    runner = _make_runner(limit_seconds=30)
    event = _make_event()

    long_answer = " ".join(["palabra"] * 90)
    assert runner._should_send_voice_reply(
        event,
        long_answer,
        agent_messages=[],
        already_sent=False,
    ) is False
