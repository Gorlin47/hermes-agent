from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


SCRIPT_PATH = Path('/home/jony/.hermes/scripts/codex_quota_low_watchdog.py')


def load_watchdog_module():
    spec = importlib.util.spec_from_file_location('codex_quota_low_watchdog_under_test', SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_empty_codex_pool_starts_debounce_without_rewriting_config_or_restarting(tmp_path, monkeypatch):
    mod = load_watchdog_module()
    config_path = tmp_path / 'config.yaml'
    failover_path = tmp_path / 'codex_provider_failover.json'
    original_model = {
        'provider': 'openai-codex',
        'default': 'gpt-5.5',
        'base_url': 'https://chatgpt.com/backend-api/codex',
    }
    config_path.write_text(
        yaml.safe_dump({
            'model': original_model,
            'fallback_providers': [
                {'provider': 'openrouter', 'model': 'gpt-5.4-mini', 'base_url': 'https://openrouter.ai/api/v1'},
            ],
        }, sort_keys=False),
        encoding='utf-8',
    )
    monkeypatch.setattr(mod, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(mod, 'FAILOVER_STATE_PATH', failover_path)
    monkeypatch.setattr(mod, 'FAILOVER_EMPTY_CONSECUTIVE_POLLS', 3)
    monkeypatch.setattr(mod, 'FAILOVER_EMPTY_GRACE_SECONDS', 180)
    restarts: list[str] = []

    messages = mod._sync_provider_failover(
        after_pool={'active': None},
        now='2026-06-17T06:29:51+00:00',
        restart_gateway=lambda: restarts.append('restart'),
    )

    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    assert cfg['model'] == original_model
    state = mod._load_failover_state()
    assert state['mode'] == 'codex-normal'
    assert state['empty_consecutive_polls'] == 1
    assert state['empty_since'] == '2026-06-17T06:29:51+00:00'
    assert state['reason'] == 'no_codex_accounts_available'
    assert restarts == []
    assert messages == []
    assert not config_path.with_suffix('.yaml.bak-codex-failover').exists()


def test_empty_codex_pool_alerts_after_debounce_without_rewriting_config_or_restarting(tmp_path, monkeypatch):
    mod = load_watchdog_module()
    config_path = tmp_path / 'config.yaml'
    failover_path = tmp_path / 'codex_provider_failover.json'
    original_model = {
        'provider': 'openai-codex',
        'default': 'gpt-5.5',
        'base_url': 'https://chatgpt.com/backend-api/codex',
    }
    config_path.write_text(
        yaml.safe_dump({'model': original_model}, sort_keys=False),
        encoding='utf-8',
    )
    monkeypatch.setattr(mod, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(mod, 'FAILOVER_STATE_PATH', failover_path)
    monkeypatch.setattr(mod, 'FAILOVER_EMPTY_CONSECUTIVE_POLLS', 3)
    monkeypatch.setattr(mod, 'FAILOVER_EMPTY_GRACE_SECONDS', 180)
    mod._save_failover_state({
        'mode': 'codex-normal',
        'empty_since': '2026-06-17T06:29:51+00:00',
        'empty_consecutive_polls': 2,
    })
    restarts: list[str] = []

    messages = mod._sync_provider_failover(
        after_pool={'active': None},
        now='2026-06-17T06:31:51+00:00',
        restart_gateway=lambda: restarts.append('restart'),
    )

    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    assert cfg['model'] == original_model
    state = mod._load_failover_state()
    assert state['mode'] == 'openrouter-emergency'
    assert state['empty_consecutive_polls'] == 3
    assert state['restart_pending'] is False
    assert state['active_provider'] == 'openrouter'
    assert state['active_model'] == 'gpt-5.4-mini'
    assert restarts == []
    assert any('fallback runtime' in message.lower() for message in messages)
    assert not config_path.with_suffix('.yaml.bak-codex-failover').exists()


def test_recovered_codex_clears_debounce_without_rewrite_or_restart(tmp_path, monkeypatch):
    mod = load_watchdog_module()
    config_path = tmp_path / 'config.yaml'
    failover_path = tmp_path / 'codex_provider_failover.json'
    original_model = {
        'provider': 'openai-codex',
        'default': 'gpt-5.5',
        'base_url': 'https://chatgpt.com/backend-api/codex',
    }
    config_path.write_text(
        yaml.safe_dump({'model': original_model}, sort_keys=False),
        encoding='utf-8',
    )
    monkeypatch.setattr(mod, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(mod, 'FAILOVER_STATE_PATH', failover_path)
    mod._save_failover_state({
        'mode': 'codex-normal',
        'empty_since': '2026-06-17T06:29:51+00:00',
        'empty_consecutive_polls': 2,
    })
    restarts: list[str] = []

    messages = mod._sync_provider_failover(
        after_pool={'active': {'id': '23fcf0', 'title': 'Codex · Jonatan'}},
        now='2026-06-17T06:31:28+00:00',
        restart_gateway=lambda: restarts.append('restart'),
    )

    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    assert cfg['model'] == original_model
    state = mod._load_failover_state()
    assert state['mode'] == 'codex-normal'
    assert state['empty_consecutive_polls'] == 0
    assert state['empty_since'] is None
    assert state['active_codex_account']['title'] == 'Codex · Jonatan'
    assert restarts == []
    assert messages == []


def test_recovered_codex_after_runtime_failover_updates_state_without_rewrite_or_restart(tmp_path, monkeypatch):
    mod = load_watchdog_module()
    config_path = tmp_path / 'config.yaml'
    failover_path = tmp_path / 'codex_provider_failover.json'
    original_model = {
        'provider': 'openai-codex',
        'default': 'gpt-5.5',
        'base_url': 'https://chatgpt.com/backend-api/codex',
    }
    config_path.write_text(
        yaml.safe_dump({'model': original_model}, sort_keys=False),
        encoding='utf-8',
    )
    monkeypatch.setattr(mod, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(mod, 'FAILOVER_STATE_PATH', failover_path)
    mod._save_failover_state({
        'mode': 'openrouter-emergency',
        'previous_model': original_model,
        'active_provider': 'openrouter',
        'active_model': 'gpt-5.4-mini',
        'reason': 'no_codex_accounts_available',
        'changed_at': '2026-06-17T06:31:51+00:00',
        'restart_pending': False,
        'empty_since': '2026-06-17T06:29:51+00:00',
        'empty_consecutive_polls': 3,
    })
    restarts: list[str] = []

    messages = mod._sync_provider_failover(
        after_pool={'active': {'id': '23fcf0', 'title': 'Codex · Jonatan'}},
        now='2026-06-17T06:35:28+00:00',
        restart_gateway=lambda: restarts.append('restart'),
    )

    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    assert cfg['model'] == original_model
    state = mod._load_failover_state()
    assert state['mode'] == 'codex-normal'
    assert state['restored_provider'] == 'openai-codex'
    assert state['restored_model'] == 'gpt-5.5'
    assert state['restart_pending'] is False
    assert state['empty_consecutive_polls'] == 0
    assert state['empty_since'] is None
    assert restarts == []
    assert any('sin reinicio' in message.lower() for message in messages)
