"""Safe tool surface for Discord realtime voice.

Realtime voice is intentionally not a full Hermes tool runtime. This module
keeps the OpenAI Realtime tool schema explicit and blocks everything outside the
small MVP allowlist.
"""

from __future__ import annotations

from typing import Any, Dict, List

REALTIME_TOOL_NAMES = frozenset(
    {
        "create_reminder",
        "web_search_summary",
        "generate_image_to_discord",
        "leave_voice_channel",
    }
)

_DENIED_MESSAGE = (
    "Eso requiere modo operativo completo, señor. "
    "Pídamelo por texto a Jarvis para ejecutarlo con seguridad."
)


def build_openai_realtime_tools() -> List[Dict[str, Any]]:
    """Return OpenAI Realtime tool schemas for the approved MVP tools only."""
    return [
        {
            "type": "function",
            "name": "create_reminder",
            "description": "Create a safe reminder from a short text and parseable time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Reminder text."},
                    "when": {"type": "string", "description": "Natural language or ISO time."},
                },
                "required": ["text", "when"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "web_search_summary",
            "description": "Look up public web information and return a concise spoken summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "generate_image_to_discord",
            "description": "Generate an image and deliver it to the linked Discord text channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Image prompt."},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "leave_voice_channel",
            "description": "Disconnect the bot from the current Discord voice channel when the user asks it to leave.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Short reason for leaving, if the user provides one.",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    ]


def dispatch_realtime_tool(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Dispatch one realtime tool request through the safe allowlist.

    Full implementations are intentionally deferred until the text-channel
    delivery and reminder routing pieces are wired. Unknown tools are rejected
    now so OpenAI Realtime can never request terminal/files/system-control.
    """
    if name not in REALTIME_TOOL_NAMES:
        return {"ok": False, "tool": name, "message": _DENIED_MESSAGE}
    return {
        "ok": True,
        "tool": name,
        "arguments": arguments or {},
        "message": f"Tool {name} pendiente de implementación segura.",
    }
