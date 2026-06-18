"""Shared Jarvis direct-mode policy helpers.

This module keeps the worker routing map and the user-facing status text in one
place so the CLI and gateway stay aligned.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JarvisWorkerRoute:
    """Human-readable worker routing rule."""

    worker: str
    responsibility: str
    escalate_when: str


JARVIS_WORKER_ROUTES: tuple[JarvisWorkerRoute, ...] = (
    JarvisWorkerRoute(
        worker="Scout",
        responsibility="Discover scope, inventory inputs, and gather first-pass facts.",
        escalate_when="the request is ambiguous, undocumented, or needs live discovery.",
    ),
    JarvisWorkerRoute(
        worker="Thinker",
        responsibility="Compare options, reason about trade-offs, and choose the path.",
        escalate_when="the task spans multiple subsystems or the right route is still unclear.",
    ),
    JarvisWorkerRoute(
        worker="Builder",
        responsibility="Implement the chosen change and produce the artifact.",
        escalate_when="the task mutates code, files, or configuration and needs verification.",
    ),
    JarvisWorkerRoute(
        worker="Reviewer",
        responsibility="Validate diffs, run checks, and catch regressions before handoff.",
        escalate_when="the change is risky, user-facing, or needs an independent sanity check.",
    ),
    JarvisWorkerRoute(
        worker="Ops",
        responsibility="Handle runtime state, service control, secrets, and other sensitive ops.",
        escalate_when="the request touches live services, credentials, cron, or deployment state.",
    ),
    JarvisWorkerRoute(
        worker="Monitor",
        responsibility="Watch for drift, thresholds, and long-running conditions.",
        escalate_when="the issue is temporal, threshold-based, or needs ongoing observation.",
    ),
    JarvisWorkerRoute(
        worker="Scribe",
        responsibility="Capture the final decision, procedure, or stable reference.",
        escalate_when="the workflow needs durable documentation or a project-note update.",
    ),
)

JARVIS_ESCALATION_RULES: tuple[str, ...] = (
    "Escalate to Jarvis when the task spans multiple subsystems, requires live verification, or carries operational risk.",
    "Keep Scout and Monitor read-only; they should gather or watch, not mutate state.",
    "Use Ops for live-service changes and secrets, Reviewer for validation, and Builder only after the route is stable.",
)


def format_jarvis_status_lines(enabled: bool) -> list[str]:
    """Render the current direct-mode state as compact user-facing lines."""

    state = "ON" if enabled else "OFF"
    return [
        f"Jarvis direct mode: {state}",
        "When ON, the main agent keeps delegation disabled and answers directly.",
        "Use /jarvis policy to inspect the worker map and escalation rules.",
    ]


def format_jarvis_policy_lines() -> list[str]:
    """Render the worker routing map and escalation rules."""

    lines = ["Jarvis worker routing:"]
    for route in JARVIS_WORKER_ROUTES:
        lines.append(
            f"  - {route.worker}: {route.responsibility} Escalate when {route.escalate_when}"
        )
    lines.append("Escalation rules:")
    for idx, rule in enumerate(JARVIS_ESCALATION_RULES, start=1):
        lines.append(f"  {idx}. {rule}")
    lines.append("Override:")
    lines.append("  /jarvis on   → enable direct mode for the current session")
    lines.append("  /jarvis off  → restore normal delegation for the current session")
    lines.append("  /jarvis <prompt> → enable direct mode and send the prompt directly")
    return lines
