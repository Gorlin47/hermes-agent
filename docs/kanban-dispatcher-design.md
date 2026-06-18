# Kanban Dispatcher Design

This document captures the dispatcher contract described in the Telegram discussion and reflects the current Hermes Kanban implementation.

## 1) Task schema

A Kanban task needs enough structure for a dispatcher to make a safe, deterministic routing decision.

Minimum fields:

- `id`: stable task identifier.
- `title`: short human-readable summary.
- `body`: detailed specification / context.
- `status`: lifecycle state.
- `assignee`: target Hermes profile or lane.
- `priority`: ordering signal within a lane.
- `tenant` / board: isolation boundary for unrelated workstreams.
- `workspace_kind` and `workspace_path`: where the worker executes.
- `parents` / links: dependency graph for promotion.
- `skills`: extra skill bundles to force-load into the worker.
- `model_override`: optional per-task model selection.
- `max_runtime_seconds`: runtime cap for the worker.
- `session_id`: origin traceability for chat-driven tasks.
- `result` / run summary: handoff payload after completion.

## 2) Routing policy

The dispatcher follows a strict sequence:

1. Reclaim stale claims and crashed workers.
2. Promote tasks from `todo` to `ready` only when dependency gates are satisfied.
3. Inspect `ready` tasks in priority order.
4. Skip tasks that are unassigned unless a default assignee is configured.
5. Skip tasks whose assignee is not a spawnable Hermes profile.
6. Respect global and per-profile concurrency caps.
7. Claim the task atomically and spawn a worker.
8. Record the worker PID and begin heartbeat / crash monitoring.

Routing must be content-aware, not heuristic mush:

- **Triage** tasks are for spec refinement only.
- **Todo** tasks are specified but waiting for dependency clearance.
- **Ready** tasks are dispatchable.
- **Running** tasks are owned by a live worker.
- **Blocked** tasks require operator action.
- **Done** tasks are complete and available as handoff context.
- **Archived** tasks are out of the active path.

## 3) Dispatcher → worker contract

When a task is claimed, the dispatcher injects:

- `HERMES_KANBAN_DB`
- `HERMES_KANBAN_WORKSPACES_ROOT`
- `HERMES_KANBAN_BOARD`
- `HERMES_PROFILE`

The worker starts under the target profile and receives:

- the built-in `kanban-worker` skill when available,
- any task-specific skills,
- the model override, if present,
- a bounded worker context containing task body, dependencies, prior attempts, comments, attachments, and parent handoffs.

The dispatcher is responsible for:

- atomic claim / claim-lock enforcement,
- per-task log creation and rotation,
- stale claim reclamation,
- crash detection,
- re-queueing or blocking on failure thresholds.

The worker is responsible for:

- executing the task,
- heartbeating when necessary,
- writing a useful summary,
- marking completion or block with a concrete reason,
- never mutating board state out-of-band.

## 4) Review and verification

A task is not done because a worker said so. It is done when:

- the output artifact exists,
- the acceptance criteria are satisfied,
- the board reflects the final state,
- and the result was verified by an independent pass.

Recommended verification order:

1. Worker produces a summary / diff / artifact.
2. Reviewer checks the artifact and acceptance criteria.
3. Operator or automation runs the canonical smoke test.
4. The task is marked `done` only after the verification step passes.

## 5) Canonical smoke task

The simplest useful smoke flow is:

1. Create a small task with a clear assignee.
2. Let the dispatcher promote it to `ready`.
3. Dispatch one pass.
4. Confirm a worker claim was created.
5. Confirm the worker context contains the task title/body.
6. Confirm the task can complete and surface a handoff summary.

That smoke task proves the board, routing, spawning, and verification loop all cooperate. The system is much more convincing when it does one boring thing correctly.

## 6) Operational notes

- The gateway hosts the embedded dispatcher in the default path.
- `hermes kanban dispatch` remains a direct manual tick for debugging.
- Unassigned work should not silently disappear.
- Non-spawnable assignees should be reported separately from unassigned work.
- Multi-board installs must remain isolated by board slug and on-disk paths.

## 7) Current implementation pointers

Relevant modules:

- `hermes_cli/kanban_db.py` — task schema, claim logic, dispatch loop, worker context.
- `hermes_cli/kanban.py` — CLI surface and manual dispatch command.
- `plugins/kanban/dashboard/plugin_api.py` — dashboard API over the same board state.
- `tests/hermes_cli/test_kanban_db.py` — dispatcher behavior tests.
- `tests/hermes_cli/test_kanban_cli.py` — command-surface smoke tests.
