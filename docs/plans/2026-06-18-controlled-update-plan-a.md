# Controlled Update Plan A

> **For Hermes:** treat the current checkout as the source archive, not as the update target. Preserve first, separate work into topic branches/patches, then replay only the approved topics onto a clean updated tree.

**Goal:** Keep the user’s local Hermes changes safe across upstream updates without relying on a dirty `main` checkout.

**Architecture:** Use a two-tree workflow. Tree A is the current dirty checkout at `/home/jony/.hermes/hermes-agent`, preserved and split into topic branches. Tree B is a fresh clean integration worktree created from upstream `origin/main`; only selected local topics are replayed there via `cherry-pick` or `git am`, then verified before any live service switch.

**Tech Stack:** git, git worktree, focused pytest, Hermes CLI health checks.

---

## Current state captured

### Snapshot created before planning
- `/tmp/jarvis-update-snapshots/pre-planA-20260618_150746.status`
- `/tmp/jarvis-update-snapshots/pre-planA-20260618_150746.patch`
- `/tmp/jarvis-update-snapshots/pre-planA-20260618_150746.cached.patch`

### Upstream relation
- Repo: `/home/jony/.hermes/hermes-agent`
- Branch: `main`
- Remote: `origin https://github.com/NousResearch/hermes-agent.git`
- Divergence vs `origin/main`: `0 ahead / 11860 behind`

### Provisional topic grouping from the live diff

#### Topic A — runtime observability / continuity (high priority, preserve first)
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

#### Topic B — account/quota/web observability (needs separate branch)
- `acp_adapter/session.py`
- `agent/account_usage.py`
- `agent/agent_runtime_helpers.py`
- `agent/conversation_loop.py`
- `cli.py`
- `gateway/config.py`
- `gateway/slash_commands.py`
- `hermes_cli/cli_commands_mixin.py`
- `hermes_cli/commands.py`
- `hermes_cli/web_server.py`
- `run_agent.py`
- `tests/hermes_cli/test_web_server_host_header.py`
- `tests/test_account_usage.py`
- `tests/scripts/test_codex_quota_low_watchdog_failover.py`

#### Topic B2 — dashboard / Tailscale host-header hotfix (separate branch, preserve for replay)
- `hermes_cli/web_server.py`
- `tests/hermes_cli/test_dashboard_auth_ws_auth.py`
- `tests/hermes_cli/test_web_server_host_header.py`

Preserved branch created after the initial split plan:
- branch: `jony/dashboard-tailscale-host-header-fix`
- commit: `54702b1174afca31b1caf95f5bb86bd0e726efbb`
- subject: `fix(dashboard): trust public_url host for tailscale reverse proxy`

Replay note:
- keep this as its own hotfix branch even though it overlaps `hermes_cli/web_server.py` with Topic B; apply it deliberately during update replay after choosing whether Topic B is also wanted.

#### Topic C — Discord realtime / voice work (separate branch, do not mix into continuity)
- `plugins/platforms/discord/adapter.py`
- `plugins/platforms/discord/voice_mixer.py`
- `plugins/platforms/discord/realtime_tools.py`
- `plugins/platforms/discord/realtime_voice.py`
- `tests/gateway/test_discord_voice_mixer.py`
- `tests/gateway/test_discord_realtime_openai_provider.py`
- `tests/gateway/test_discord_realtime_voice_session.py`
- `tests/gateway/test_discord_voice_realtime.py`
- `package-lock.json`

#### Topic D — policy / kanban / docs / other workstreams (review separately)
- `docs/kanban-dispatcher-design.md`
- `docs/plans/discord-realtime-voice.md`
- `hermes_cli/jarvis_policy.py`
- `skills/software-development/kanban-dispatcher/SKILL.md`
- `tests/gateway/test_jarvis_command.py`

#### Topic E — TTS / Telegram voice length work (separate branch)
- `tools/tts_tool.py`
- `tests/tools/test_tts_speed.py`
- `tests/gateway/test_telegram_voice_reply_length.py`

> These groupings are the starting partition for Plan A. They are intentionally conservative: if a file is ambiguous, it stays isolated instead of being merged into the wrong branch.

---

## Phase 1: Freeze and preserve the dirty checkout

### Task 1: Refresh discovery and capture exact repo state
**Objective:** Record the precise starting point before any branch surgery.

**Files:**
- Read only: `/home/jony/.hermes/hermes-agent/.git/`
- Output artifacts under: `/tmp/jarvis-update-snapshots/`

**Commands:**
```bash
git status --short --branch
git fetch --all --prune
git rev-list --left-right --count HEAD...origin/main
git diff --stat
```

**Verification:**
- status still matches the expected dirty tree
- upstream relation is recorded
- no hidden staged changes appear unexpectedly

### Task 2: Create an external safety bundle
**Objective:** Have a portable git backup independent of branch names or stashes.

**Commands:**
```bash
mkdir -p ~/.hermes/update-backups/$(date +%Y%m%d)
git bundle create ~/.hermes/update-backups/$(date +%Y%m%d)/hermes-agent-pre-planA.bundle --all
```

**Verification:**
```bash
git bundle verify ~/.hermes/update-backups/$(date +%Y%m%d)/hermes-agent-pre-planA.bundle
```
Expected: bundle verifies successfully.

### Task 3: Export topic candidate patches
**Objective:** Preserve replayable patches even before making topic commits.

**Commands:**
```bash
mkdir -p ~/.hermes/update-backups/$(date +%Y%m%d)/patches
```
Then export at minimum:
```bash
git diff -- agent/turn_context.py gateway/run.py gateway/runtime_footer.py \
  tests/agent/test_turn_context.py tests/gateway/test_runtime_footer.py \
  tests/run_agent/test_primary_runtime_restore.py tests/test_tui_gateway_server.py \
  tui_gateway/server.py tui_gateway/slash_worker.py \
  ui-tui/src/__tests__/appChromeStatusRule.test.tsx \
  ui-tui/src/__tests__/createGatewayEventHandler.test.ts \
  ui-tui/src/app/createGatewayEventHandler.ts ui-tui/src/app/interfaces.ts \
  ui-tui/src/app/uiStore.ts ui-tui/src/components/appChrome.tsx \
  ui-tui/src/components/appLayout.tsx ui-tui/src/gatewayTypes.ts \
  > ~/.hermes/update-backups/$(date +%Y%m%d)/patches/runtime-observability.patch
```
Repeat for each topic.

**Verification:**
- each patch file exists
- `wc -l` is non-zero for every expected non-empty patch

---

## Phase 2: Split local work into topic branches

### Task 4: Preserve current dirty checkout as archive branch
**Objective:** Ensure the current mixed state remains reachable before selective cleanup.

**Commands:**
```bash
git branch archive/pre-planA-dirty-$(date +%Y%m%d)
```

**Verification:**
```bash
git branch --list 'archive/pre-planA-dirty-*'
```
Expected: new archive branch is listed.

### Task 5: Create the first keep branch for continuity/runtime
**Objective:** Isolate the high-value runtime observability work into its own branch.

**Commands:**
```bash
git switch -c jony/runtime-observability
```
Then stage only Topic A files:
```bash
git add agent/turn_context.py gateway/run.py gateway/runtime_footer.py \
  tests/agent/test_turn_context.py tests/gateway/test_runtime_footer.py \
  tests/run_agent/test_primary_runtime_restore.py tests/test_tui_gateway_server.py \
  tui_gateway/server.py tui_gateway/slash_worker.py \
  ui-tui/src/__tests__/appChromeStatusRule.test.tsx \
  ui-tui/src/__tests__/createGatewayEventHandler.test.ts \
  ui-tui/src/app/createGatewayEventHandler.ts ui-tui/src/app/interfaces.ts \
  ui-tui/src/app/uiStore.ts ui-tui/src/components/appChrome.tsx \
  ui-tui/src/components/appLayout.tsx ui-tui/src/gatewayTypes.ts
```

**Verification:**
```bash
git diff --cached --stat
```
Expected: only Topic A files appear.

### Task 6: Verify Topic A before commit
**Objective:** Prove the isolated branch is real, not decorative.

**Commands:**
```bash
./venv/bin/python -m pytest -o addopts='' tests/test_tui_gateway_server.py
./venv/bin/python -m pytest -o addopts='' tests/gateway/test_runtime_footer.py tests/agent/test_turn_context.py tests/run_agent/test_primary_runtime_restore.py
```
Expected:
- `tests/test_tui_gateway_server.py` passes
- runtime block passes

### Task 7: Commit Topic A cleanly
**Objective:** Produce a replayable commit for the update path.

**Command:**
```bash
git commit -m "feat: preserve runtime observability across tui turns"
```

**Verification:**
```bash
git show --stat --summary HEAD
```
Expected: commit touches only Topic A files.

### Task 8: Repeat branch split for remaining topics
**Objective:** Create one branch per unrelated workstream.

**Suggested branches:**
```text
jony/account-quota-observability
jony/discord-realtime-voice
jony/policy-kanban-docs
jony/tts-voice-length
```

**Method:**
- switch back to `archive/pre-planA-dirty-YYYYMMDD`
- create a new topic branch from it
- stage only that topic’s files
- run focused tests for that topic
- commit

**Verification:**
- each branch has one coherent topic commit set
- no branch mixes unrelated surfaces

---

## Phase 3: Create a clean integration tree for the update

### Task 9: Create a clean worktree from upstream
**Objective:** Build the updated candidate in isolation instead of mutating the dirty tree.

**Commands:**
```bash
git fetch --all --prune
git worktree add ../hermes-agent-updated origin/main
```

**Verification:**
```bash
git -C ../hermes-agent-updated status --short --branch
```
Expected: clean detached tree or branch rooted at `origin/main`.

### Task 10: Create an integration branch in the clean tree
**Objective:** Keep replay work off detached HEAD.

**Commands:**
```bash
git -C ../hermes-agent-updated switch -c jony/integration-2026-06-controlled-update
```

**Verification:**
```bash
git -C ../hermes-agent-updated branch --show-current
```
Expected: `jony/integration-2026-06-controlled-update`

### Task 11: Replay only approved topic commits
**Objective:** Bring forward the local work we actually want.

**Preferred command:**
```bash
git -C ../hermes-agent-updated cherry-pick <topic-commit-sha>
```
Alternative if preserving as mail patches:
```bash
git -C ../hermes-agent-updated am ~/.hermes/update-backups/<date>/patches/runtime-observability.patch
```

**Verification:**
- cherry-pick or `git am` completes
- conflicts are resolved only in the clean integration tree
- runtime/tests still make sense against upstream

---

## Phase 4: Validate the clean updated integration tree

### Task 12: Run focused regression tests on replayed work
**Objective:** Confirm the preserved features survived upstream.

**Commands for Topic A:**
```bash
./venv/bin/python -m pytest -o addopts='' tests/test_tui_gateway_server.py
./venv/bin/python -m pytest -o addopts='' tests/gateway/test_runtime_footer.py tests/agent/test_turn_context.py tests/run_agent/test_primary_runtime_restore.py
```

**Additional health checks:**
```bash
hermes --version
hermes doctor
hermes status --all
```

**Verification:**
- tests pass in the clean updated tree
- no new obvious health regressions appear

### Task 13: Validate the live surface before any service switch
**Objective:** Confirm the UI/runtime path still behaves correctly outside unit tests.

**Checks:**
- dashboard starts cleanly
- `message.complete` still carries structured `runtime`
- TUI status bar still shows the compact runtime badge
- primary model remains visible while fallback is execution-time only

---

## Phase 5: Promote the updated tree only after verification

### Task 14: Decide the promotion strategy
**Objective:** Change production only after the clean tree is trusted.

**Preferred options:**
1. Keep old tree as archive and repoint service/workflow to the clean updated tree.
2. Or replace the original checkout only after a final backup of the archived one.

**Do not do:**
- `git pull` into the dirty archive tree
- destructive reset before topic branches and bundle exist

### Task 15: Post-update retention policy
**Objective:** Make future updates cheaper.

**Policy:**
- user work never lives long-term on `main`
- each local feature gets its own branch immediately
- before each update: bundle + patches + focused test list
- if a feature should survive updates permanently, consider upstreaming it or moving it into a plugin/profile-local extension when that is architecturally cleaner

---

## Immediate recommended execution order

1. Refresh discovery (`git fetch`, status, diff stat)
2. Create `git bundle`
3. Export Topic A patch
4. Create archive branch from the current dirty tree
5. Create `jony/runtime-observability`
6. Stage only Topic A files
7. Re-run Topic A tests
8. Commit Topic A cleanly
9. Repeat for the remaining topics
10. Only then create `../hermes-agent-updated` worktree and start replay

---

## Acceptance criteria

Plan A is successful when all of these are true:
- the current dirty state is recoverable via archive branch + bundle + patch exports
- runtime observability is isolated in a replayable commit or branch
- unrelated workstreams are separated into their own branches
- a clean updated worktree exists from upstream
- only approved local topics are replayed there
- focused tests pass in the updated tree before any live switch

---

## Notes specific to this repo

- The continuity/runtime work is the first preservation target because it is already validated and directly tied to user-visible reliability.
- The repo is far behind upstream; conflict handling belongs in the clean integration tree, not in the archive tree.
- If a preserved topic keeps fighting upstream every update, that is a signal to upstream it, pluginize it, or move it into a profile-local extension instead of carrying it indefinitely as a private patch stack.
