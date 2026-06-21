from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from hermes_cli import profiles
from hermes_constants import get_hermes_home

DEFAULT_DESKTOP_BRANDING: dict[str, Any] = {
    "version": 1,
    "wordmark": "J.A.R.V.I.S.",
    "tagline": "Just A Rather Very Intelligent System",
    "status_label": "Autonomous operator",
    "avatar_letter": "J",
    "theme": {
        "accent": "#22d3ee",
        "accent_soft": "rgba(34,211,238,0.18)",
        "text": "#e6f7ff",
    },
    "intro_copy": [
        {
            "headline": "What should J.A.R.V.I.S. look at?",
            "body": "Send the task, failing path, or half-formed plan. I'll help turn it into action.",
        },
        {
            "headline": "Where should we start?",
            "body": "Bring the problem, goal, or file. I'll inspect first and keep the next step concrete.",
        },
    ],
}


def _profile_key(profile: str | None) -> str:
    value = (profile or "").strip()
    if not value or value.lower() == "current":
        return profiles.get_active_profile_name()

    canon = profiles.normalize_profile_name(value)
    profiles.validate_profile_name(canon)
    return canon


def _current_profile_home(key: str) -> Path:
    if key == profiles.get_active_profile_name():
        return get_hermes_home()
    return profiles.get_profile_dir(key)


def _candidate_paths(profile: str | None) -> list[tuple[str, Path]]:
    key = _profile_key(profile)
    default_home = profiles.get_profile_dir("default")
    candidates: list[tuple[str, Path]] = []

    if key != "default":
        candidates.append(("profile", _current_profile_home(key) / "desktop-branding.yaml"))

    candidates.append((("default" if key == "default" else "global"), default_home / "desktop-branding.yaml"))
    return candidates


def _read_branding_file(path: Path) -> dict[str, Any] | None:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except yaml.YAMLError:
        return None

    if not isinstance(raw, dict):
        return None
    return raw


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _clean_intro_copy(value: Any, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return deepcopy(fallback)

    cleaned: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        headline = _clean_text(item.get("headline"))
        body = _clean_text(item.get("body"))
        if headline and body:
            cleaned.append({"headline": headline, "body": body})

    return cleaned or deepcopy(fallback)


def _merge_branding(raw: dict[str, Any], *, source: str, profile: str) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_DESKTOP_BRANDING)

    for key in ("wordmark", "tagline", "status_label", "avatar_letter"):
        cleaned = _clean_text(raw.get(key))
        if cleaned:
            merged[key] = cleaned

    theme = raw.get("theme")
    if isinstance(theme, dict):
        for key in ("accent", "accent_soft", "text"):
            cleaned = _clean_text(theme.get(key))
            if cleaned:
                merged["theme"][key] = cleaned

    merged["intro_copy"] = _clean_intro_copy(raw.get("intro_copy"), DEFAULT_DESKTOP_BRANDING["intro_copy"])
    merged["source"] = source
    merged["profile"] = profile
    return merged


def load_desktop_branding(profile: str | None) -> dict[str, Any]:
    key = _profile_key(profile)
    for source, path in _candidate_paths(key):
        if not path.exists():
            continue
        raw = _read_branding_file(path)
        if raw is None:
            continue
        return _merge_branding(raw, source=source, profile=key)

    payload = deepcopy(DEFAULT_DESKTOP_BRANDING)
    payload["source"] = "fallback"
    payload["profile"] = key
    return payload
