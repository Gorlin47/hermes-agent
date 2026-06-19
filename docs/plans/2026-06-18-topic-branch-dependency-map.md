# Topic branch dependency map — 2026-06-18

## Purpose
This document records the dependency structure of the local topic branches extracted from the preserved mixed snapshot (`archive/pre-planA-dirty-20260618-151742`).

It exists so future replay/cherry-pick work does **not** depend on memory, guesswork, or broad "take the whole thing" merges.

## Source snapshot
- Archive branch: `archive/pre-planA-dirty-20260618-151742`
- Archive commit: `5affd2cfcace88e391f21e4fa54f884e49e201af`

## Base facts
All topic branches currently fork from the same old local `main` base:

- common merge-base vs `main`: `a3fca26c562023fdfb9d0efdcc608e946fdfca02`
- common merge-base vs `origin/main`: `a3fca26c562023fdfb9d0efdcc608e946fdfca02`

That means the graph is **flat in git ancestry**, but not flat in practical replay terms. Some branches were intentionally built on top of `jony/runtime-observability` because they share gateway/runtime surface and were only testable that way.

## Branch inventory

### 1) Runtime / observability base block
- Branch: `jony/runtime-observability`
- Commit: `11ee2a705dc48c2deb67d0f2219ddc2364a8c426`
- Subject: `jarvis: feat: preserve runtime observability across tui turns`

Files in this block:
- `agent/agent_runtime_helpers.py`
- `agent/turn_context.py`
- `gateway/run.py`
- `gateway/runtime_footer.py`
- `tests/agent/test_turn_context.py`
- `tests/gateway/test_runtime_footer.py`
- `tests/run_agent/test_primary_runtime_restore.py`
- `tests/test_tui_gateway_server.py`
- `tui_gateway/server.py`
- `tui_gateway/slash_worker.py`
- `ui-tui/src/__tests__/appChromeStatusRule.test.tsx`
- `ui-tui/src/__tests__/createGatewayEventHandler.test.ts`
- `ui-tui/src/app/createGatewayEventHandler.ts`
- `ui-tui/src/app/interfaces.ts`
- `ui-tui/src/app/uiStore.ts`
- `ui-tui/src/components/appChrome.tsx`
- `ui-tui/src/components/appLayout.tsx`
- `ui-tui/src/gatewayTypes.ts`

Status:
- Treat this as the **practical base** for several later branches.
- If replaying gateway/TUI work elsewhere, apply this block first.

---

### 2) Account / quota / web observability
- Branch: `jony/account-quota-observability`
- Commit: `6674720ecc6905eedd33ccb496e5a01af2262862`
- Subject: `jarvis: feat: isolate account quota observability controls`

Files in this block:
- `acp_adapter/session.py`
- `agent/account_usage.py`
- `agent/agent_init.py`
- `agent/conversation_loop.py`
- `cli.py`
- `gateway/config.py`
- `gateway/slash_commands.py`
- `hermes_cli/cli_commands_mixin.py`
- `hermes_cli/commands.py`
- `hermes_cli/web_server.py`
- `run_agent.py`
- `tests/hermes_cli/test_web_server_host_header.py`
- `tests/scripts/test_codex_quota_low_watchdog_failover.py`
- `tests/test_account_usage.py`

Status:
- **Independent from runtime in ancestry and practical replay.**
- Can be replayed directly from `main` when needed.

Crossovers to remember:
- Shares `gateway/slash_commands.py` with `jony/discord-realtime-voice`
- Shares `gateway/slash_commands.py` with `jony/jarvis-policy-kanban`
- Shares `gateway/config.py` with `jony/tts-voice-length`

---

### 3) Discord realtime voice
- Branch: `jony/discord-realtime-voice`
- Commit: `1e04e9474b726067132d6cb4e46bf7f5f83e3777`
- Subject: `jarvis: feat: isolate discord realtime voice work`

Practical base:
- `jony/runtime-observability`

Why:
- This branch includes the full runtime block surface because replay/testing exposed a real dependency on the shared gateway/runtime path.
- The branch **contains** the runtime commit logically and was validated on top of it.

Delta relative to `jony/runtime-observability`:
- `docs/plans/discord-realtime-voice.md`
- `gateway/slash_commands.py`
- `package-lock.json`
- `plugins/platforms/discord/adapter.py`
- `plugins/platforms/discord/realtime_tools.py`
- `plugins/platforms/discord/realtime_voice.py`
- `plugins/platforms/discord/voice_mixer.py`
- `tests/gateway/test_discord_realtime_openai_provider.py`
- `tests/gateway/test_discord_realtime_voice_session.py`
- `tests/gateway/test_discord_voice_mixer.py`
- `tests/gateway/test_discord_voice_realtime.py`

Status:
- **Replay order:** apply runtime first, then this branch.

Notes:
- `gateway/run.py` dependency comes from the runtime base already being present.
- `gateway/slash_commands.py` is the branch-specific router surface that must travel with Discord realtime.
- `tests/gateway/test_discord_voice_mixer.py` has async tests that need `pytest-asyncio` in the environment; that was an environment limitation during verification, not evidence that the branch boundary was wrong.

---

### 4) Jarvis policy / direct mode / kanban docs
- Branch: `jony/jarvis-policy-kanban`
- Commit: `430706bfcbd39079873ad170e73ffa72bd562f0a`
- Subject: `jarvis: feat: isolate jarvis policy and kanban docs`

Practical base:
- `jony/runtime-observability`

Why:
- This branch was also validated on top of the runtime block because it shares the active gateway/session surface.

Delta relative to `jony/runtime-observability`:
- `docs/kanban-dispatcher-design.md`
- `gateway/slash_commands.py`
- `hermes_cli/jarvis_policy.py`
- `skills/software-development/kanban-dispatcher/SKILL.md`
- `tests/gateway/test_jarvis_command.py`

Status:
- **Replay order:** apply runtime first, then this branch.

Notes:
- Real crossover with account/Discord is `gateway/slash_commands.py`.
- If multiple slash-command branches are replayed together later, expect a manual merge point there.

---

### 5) TTS / Telegram voice-length gating
- Branch: `jony/tts-voice-length`
- Commit: `03797ee49c6de2f69a0ea3d7377b9578ca0002fd`
- Subject: `jarvis: feat: isolate telegram voice reply length gating`

Practical base:
- `jony/runtime-observability`

Why:
- Verification showed the block needed the runtime-side gateway surface present.

Delta relative to `jony/runtime-observability`:
- `gateway/config.py`
- `tests/gateway/test_telegram_voice_reply_length.py`
- `tests/tools/test_tts_speed.py`
- `tools/tts_tool.py`

Status:
- **Replay order:** apply runtime first, then this branch.

Notes:
- Real crossover with account/quota is `gateway/config.py`.
- If both branches are replayed later, expect a merge point there.

---

### 6) Controlled-update docs
- Branch: `jony/controlled-update-docs`
- Commit: `fe0eeb19d306054e80046ef2a6aac47379ab1e97`
- Subject: `jarvis: docs: preserve controlled update plan A`

Files in this block:
- `docs/plans/2026-06-18-controlled-update-plan-a.md`

Status:
- **Independent documentation-only branch.**
- Can be replayed at any time or ignored entirely.

---

### 7) Dashboard / Tailscale host-header fix
- Branch: `jony/dashboard-tailscale-host-header-fix`
- Commit: `54702b1174afca31b1caf95f5bb86bd0e726efbb`
- Subject: `fix(dashboard): trust public_url host for tailscale reverse proxy`

Files in this block:
- `hermes_cli/web_server.py`
- `tests/hermes_cli/test_dashboard_auth_ws_auth.py`
- `tests/hermes_cli/test_web_server_host_header.py`

Status:
- **Independent hotfix branch.**
- Can be replayed directly from `main` or from a clean update worktree.
- Intended to preserve the local fix that allows a loopback-bound dashboard behind Tailscale Serve to trust the operator-declared `HERMES_DASHBOARD_PUBLIC_URL` host/origin.

Crossovers to remember:
- Shares `hermes_cli/web_server.py` with `jony/account-quota-observability`
- Shares `tests/hermes_cli/test_web_server_host_header.py` with `jony/account-quota-observability`

Verification at creation time:
- focused pytest passed for the two dashboard auth/host-header test files
- live `curl` checks returned `200 OK` on published dashboard ports `9119`, `9121`, and `9123` with the Tailscale host header

---

## Dependency summary

### Independent branches
These can be replayed directly from `main` without requiring runtime first:
- `jony/account-quota-observability`
- `jony/controlled-update-docs`
- `jony/dashboard-tailscale-host-header-fix`

### Runtime-rooted branches
These should be treated as stacked on the runtime block in practical replay order:
1. `jony/runtime-observability`
2. then one or more of:
   - `jony/discord-realtime-voice`
   - `jony/jarvis-policy-kanban`
   - `jony/tts-voice-length`

### Likely manual merge points if combining branches later
- `gateway/slash_commands.py`
  - touched by account/quota
  - touched by Discord realtime
  - touched by Jarvis policy
- `gateway/config.py`
  - touched by account/quota
  - touched by TTS voice-length gating
- `gateway/run.py`
  - shared through runtime-rooted stacks
- TUI/runtime test files and UI-TUI status files
  - shared through runtime-rooted stacks

## Recommended future replay order
If a future stable upstream update is worth replaying onto, the safest order is:

1. Replay `jony/runtime-observability`
2. Replay `jony/account-quota-observability`
3. Replay `jony/dashboard-tailscale-host-header-fix`
4. Replay whichever runtime-rooted feature branches are still wanted:
   - `jony/discord-realtime-voice`
   - `jony/jarvis-policy-kanban`
   - `jony/tts-voice-length`
5. Replay `jony/controlled-update-docs` only if the docs are still useful

Rationale:
- runtime is the most structurally shared block
- account/quota and dashboard-host fix are independent but both overlap web-server/dashboard surfaces
- Discord/Jarvis/TTS then resolve their smaller crossover points explicitly

## Coverage check
The union of the isolated topic branches covers the full preserved archive diff.

Verified result at time of writing:
- missing files from topic union: none
- extra files not in archive: none

## Operational rule going forward
Do **not** treat these branches as a promise that they will all cherry-pick cleanly forever.
Treat them as:
- preserved intent,
- minimized surfaces,
- known merge points,
- and a much safer starting position than the original mixed tree.

That is, frankly, the whole point.
