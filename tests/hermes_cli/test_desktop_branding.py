import pytest
import yaml


def test_load_desktop_branding_defaults_when_no_files(monkeypatch, _isolate_hermes_home):
    from hermes_constants import get_hermes_home
    from hermes_cli import profiles
    from hermes_cli.desktop_branding import load_desktop_branding

    default_home = get_hermes_home()
    profiles_root = default_home / "profiles"
    worker_home = profiles_root / "worker_beta"
    worker_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(profiles, "_get_default_hermes_home", lambda: default_home)
    monkeypatch.setattr(profiles, "_get_profiles_root", lambda: profiles_root)

    payload = load_desktop_branding(None)

    assert payload["version"] == 1
    assert payload["wordmark"] == "J.A.R.V.I.S."
    assert payload["source"] == "fallback"
    assert payload["profile"] == "default"
    assert payload["intro_copy"]


def test_load_desktop_branding_uses_named_profile_file(monkeypatch, _isolate_hermes_home):
    from hermes_constants import get_hermes_home
    from hermes_cli import profiles
    from hermes_cli.desktop_branding import load_desktop_branding

    default_home = get_hermes_home()
    profiles_root = default_home / "profiles"
    worker_home = profiles_root / "worker_beta"
    worker_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(profiles, "_get_default_hermes_home", lambda: default_home)
    monkeypatch.setattr(profiles, "_get_profiles_root", lambda: profiles_root)

    (worker_home / "desktop-branding.yaml").write_text(
        yaml.safe_dump(
            {
                "wordmark": "FRIDAY",
                "tagline": "Fast conversational assistant",
                "status_label": "Lightweight frontend",
                "avatar_letter": "F",
                "intro_copy": [{"headline": "Ready when you are.", "body": "Bring the task."}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = load_desktop_branding("worker_beta")

    assert payload["wordmark"] == "FRIDAY"
    assert payload["tagline"] == "Fast conversational assistant"
    assert payload["status_label"] == "Lightweight frontend"
    assert payload["avatar_letter"] == "F"
    assert payload["source"] == "profile"
    assert payload["profile"] == "worker_beta"


def test_load_desktop_branding_falls_back_to_global_for_named_profile(monkeypatch, _isolate_hermes_home):
    from hermes_constants import get_hermes_home
    from hermes_cli import profiles
    from hermes_cli.desktop_branding import load_desktop_branding

    default_home = get_hermes_home()
    profiles_root = default_home / "profiles"
    worker_home = profiles_root / "worker_beta"
    worker_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(profiles, "_get_default_hermes_home", lambda: default_home)
    monkeypatch.setattr(profiles, "_get_profiles_root", lambda: profiles_root)

    (default_home / "desktop-branding.yaml").write_text(
        yaml.safe_dump({"wordmark": "GLOBAL", "tagline": "Shared branding"}, sort_keys=False),
        encoding="utf-8",
    )

    payload = load_desktop_branding("worker_beta")

    assert payload["wordmark"] == "GLOBAL"
    assert payload["tagline"] == "Shared branding"
    assert payload["source"] == "global"
    assert payload["profile"] == "worker_beta"


def test_load_desktop_branding_invalid_root_uses_fallback(monkeypatch, _isolate_hermes_home):
    from hermes_constants import get_hermes_home
    from hermes_cli.desktop_branding import load_desktop_branding

    default_home = get_hermes_home()
    (default_home / "desktop-branding.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    payload = load_desktop_branding(None)

    assert payload["wordmark"] == "J.A.R.V.I.S."
    assert payload["source"] == "fallback"


def test_load_desktop_branding_merges_partial_theme_and_filters_bad_copy(monkeypatch, _isolate_hermes_home):
    from hermes_constants import get_hermes_home
    from hermes_cli.desktop_branding import DEFAULT_DESKTOP_BRANDING, load_desktop_branding

    default_home = get_hermes_home()
    (default_home / "desktop-branding.yaml").write_text(
        yaml.safe_dump(
            {
                "theme": {"accent": "#ff9900"},
                "intro_copy": [
                    {"headline": "Valid", "body": "Keeps this item."},
                    {"headline": "Missing body"},
                    "bad-item",
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = load_desktop_branding(None)

    assert payload["theme"]["accent"] == "#ff9900"
    assert payload["theme"]["accent_soft"] == DEFAULT_DESKTOP_BRANDING["theme"]["accent_soft"]
    assert payload["theme"]["text"] == DEFAULT_DESKTOP_BRANDING["theme"]["text"]
    assert payload["intro_copy"] == [{"headline": "Valid", "body": "Keeps this item."}]
    assert payload["source"] == "default"


def test_load_desktop_branding_uses_custom_hermes_home_for_current_profile(monkeypatch, tmp_path):
    from hermes_cli import profiles
    from hermes_cli.desktop_branding import load_desktop_branding

    custom_home = tmp_path / "custom-home"
    custom_home.mkdir(parents=True, exist_ok=True)
    profiles_root = custom_home / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)
    default_home = tmp_path / "default-home"
    default_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(profiles, "_get_default_hermes_home", lambda: default_home)
    monkeypatch.setattr(profiles, "_get_profiles_root", lambda: profiles_root)
    monkeypatch.setenv("HERMES_HOME", str(custom_home))

    (custom_home / "desktop-branding.yaml").write_text(
        yaml.safe_dump({"wordmark": "CUSTOM", "tagline": "Custom deployment"}, sort_keys=False),
        encoding="utf-8",
    )

    payload = load_desktop_branding(None)

    assert payload["wordmark"] == "CUSTOM"
    assert payload["tagline"] == "Custom deployment"
    assert payload["source"] == "profile"
    assert payload["profile"] == "custom"


def test_load_desktop_branding_rejects_invalid_profile_name(_isolate_hermes_home):
    from hermes_cli.desktop_branding import load_desktop_branding

    with pytest.raises(ValueError):
        load_desktop_branding("../escape")
