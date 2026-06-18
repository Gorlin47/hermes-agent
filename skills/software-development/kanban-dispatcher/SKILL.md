---
name: kanban-dispatcher
description: Use when designing, reviewing, or implementing Hermes Kanban routing, worker contracts, lifecycle states, and completion criteria. Keeps dispatcher behavior deterministic and verifiable.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, dispatcher, routing, workers, lifecycle, verification]
    related_skills: [software-development/subagent-driven-development, software-development/test-driven-development, software-development/requesting-code-review]
---

# Hermes Kanban Dispatcher

## Overview

Use this skill when the task is to design, modify, or reason about Hermes Kanban dispatcher behavior: what gets routed, to which worker, under which state transitions, and how completion is accepted. The dispatcher is a control-plane component, not a general-purpose worker. Its job is to make routing deterministic, keep lifecycle state consistent, and refuse to mark work done without a verifiable artifact.

This skill is intentionally operational. It favors exact states, clear contracts, and testable acceptance criteria over vague coordination language. If a routing rule cannot be checked in code or by a board query, it is not a routing rule; it is a wish.

## When to Use

- Designing the Kanban dispatcher or dispatcher daemon
- Adding or changing routing rules between task states and worker roles
- Defining worker contracts, claim semantics, logs, heartbeats, or completion gates
- Reviewing whether a task should be assigned to Scout, Thinker, Builder, Reviewer, Ops, Monitor, or Scribe
- Specifying smoke tests for board promotion, dispatch, and completion
- Debugging cases where tasks are claimed but not spawned, or spawned but never verified

Do not use this skill for:

- Purely local feature work that does not touch Kanban routing
- One-off task content editing without lifecycle implications
- Human-only project management that does not require worker automation

## Core Model

Treat the system as four layers:

1. **Conversation** — user discussion in chat.
2. **Control plane** — `/jarvis` or operator mode that can inspect and steer the board.
3. **Kanban board** — source of truth for work state.
4. **Dispatcher** — routes tasks to workers; it does not own the work itself.

The dispatcher must always preserve this separation:

- chat can describe work,
- the board records work,
- the dispatcher routes work,
- the worker executes work.

## Canonical Task States

Use a small state machine with explicit meaning:

- `triage` — rough idea, needs specification.
- `todo` — specified, waiting for dependency clearance.
- `ready` — dispatchable now.
- `running` — claimed by a live worker.
- `blocked` — cannot continue until an external condition changes.
- `done` — completed and verified.
- `archived` — no longer active.

State rules:

- A `triage` task must be specified before dispatch.
- A `todo` task only becomes `ready` when all parent/dependency gates are satisfied.
- A `ready` task may be claimed exactly once per worker attempt.
- A `running` task must have a live claim, logs, and a heartbeat path.
- A task becomes `done` only after artifact verification, not after self-report.
- A `blocked` task must carry a concrete block reason and a path to unblocking.

## Routing Roles

Map work to the narrowest role that can safely finish it:

- **Scout** — discovery, inventory, inspection, finding facts.
- **Thinker** — analysis, strategy, ambiguity reduction, decision framing.
- **Builder** — implementation, code changes, mechanical edits.
- **Reviewer** — validation, diff review, QA, acceptance checking.
- **Ops** — runtime, deploys, envs, processes, permissions, cron, services.
- **Monitor** — quota watch, status watch, alerts, temporal surveillance.
- **Scribe** — documentation, summaries, handoffs, state narration.

Routing heuristics:

- If the request is unclear, route to **Thinker** first.
- If the request needs code changes, route to **Builder** after the scope is clear.
- If the work is already implemented or needs judgment on output quality, route to **Reviewer**.
- If the work touches services, processes, cron, permissions, or environment state, route to **Ops**.
- If the work is about watching a condition over time, route to **Monitor**.
- If the work is to explain, summarize, or preserve the result, route to **Scribe**.
- If the task is about finding the right file, session, or artifact, route to **Scout**.

## Dispatcher Rules

1. **Deterministic routing first.** Base the decision on task content, dependencies, and required artifacts. Do not rely on intuition alone.
2. **Ambiguity goes to Thinker.** Do not send a vague task straight to Builder.
3. **No fake completion.** A worker saying "done" is not enough. Require the artifact, logs, diff, or test result that proves it.
4. **No orphaned work.** Every spawned worker must have an owner, a log path, and a clear success condition.
5. **One task, one primary lane.** Do not split a task across multiple workers unless there is an explicit handoff boundary.
6. **Respect dependencies.** Parent tasks must be complete or explicitly resolved before dependent children are promoted.
7. **Respect limits.** Honor concurrency caps, runtime caps, and profile isolation.
8. **Reclaim failures.** If a claim crashes or stalls, reclaim it before spawning a replacement.

## Worker Contract

When the dispatcher spawns a worker, it must provide:

- task id
- title
- body/spec
- status
- assignee / profile
- workspace path or isolation boundary
- dependency context
- attachments
- relevant prior attempts
- accepted skills or lane context
- runtime cap, if any

The worker must:

- read the task context before acting,
- keep changes scoped,
- preserve board isolation,
- emit a useful summary,
- record failures with reasons,
- never self-mark completion without an artifact.

The dispatcher must:

- claim atomically,
- pass the correct env/context,
- create logs per task,
- monitor worker health,
- move the task only when verification succeeds.

## Completion Criteria

A task is complete only when all of these are true:

- the requested artifact exists,
- acceptance criteria are satisfied,
- verification was run,
- the result was reviewed independently,
- the board state reflects the outcome,
- the handoff is useful to a future operator.

If any of these are missing, the task is not done. It may be progressing, but it is not done. Subtle distinction; annoyingly important.

## Recommended Operating Sequence

1. **Classify** the task: triage, todo, ready, blocked, or done.
2. **Route** the task: Scout / Thinker / Builder / Reviewer / Ops / Monitor / Scribe.
3. **Validate dependencies** and workspace isolation.
4. **Claim** the task atomically.
5. **Spawn** the worker with the correct env and skill context.
6. **Watch** logs, heartbeats, and failure thresholds.
7. **Verify** the artifact independently.
8. **Promote** the task state only after verification passes.

## Common Pitfalls

1. **Treating chat as source of truth.** The board is the source of truth; chat is commentary.
2. **Routing vague work directly to Builder.** This produces churn and half-finished diffs.
3. **Accepting worker self-report as completion.** Always verify with artifacts or tests.
4. **Ignoring dependencies.** A child task that bypasses parents creates hidden state bugs.
5. **Mixing control-plane and execution concerns.** The dispatcher routes; the worker executes.
6. **Leaving claims unreclaimed.** Stale claims make boards look busier than they are.
7. **Using broad roles when a narrower one is available.** Precision reduces wasted context.

## Verification Checklist

- [ ] Task state names are explicit and consistent with the board
- [ ] Routing decision is based on task content and dependency state
- [ ] Ambiguous work is routed to Thinker before Builder
- [ ] Dispatcher does not mark tasks done without verification
- [ ] Worker contract includes context, env, logs, and acceptance criteria
- [ ] Failure / reclaim / retry behavior is defined
- [ ] Smoke test exists for create → classify → dispatch → verify → complete
- [ ] Documentation or skill output matches the repo’s actual Kanban implementation

## Reference Pointers

- `docs/kanban-dispatcher-design.md`
- `hermes_cli/kanban.py`
- `hermes_cli/kanban_db.py`
- `tests/hermes_cli/test_kanban_cli.py`
- `tests/hermes_cli/test_kanban_db.py`
