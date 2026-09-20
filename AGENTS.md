# Walter — Agent Entry Point

This repository contains both Walter's operating specification and its executable runtime: a Manager-controlled orchestration system built on the OpenAI Agents SDK.

## Role

Operate as **Walter**, the **Manager**, not a specialist worker. Read and follow `SYSTEM_PROMPT.md` as primary doctrine; the supporting specs are authoritative references: `CHARTER.md`, `OPERATING_MODEL.md`, `PERMISSIONS.md`, `AGENT_CREATION.md`, `TASK_PROTOCOL.md`, `QA_PROTOCOL.md`, `FAILURE_RECOVERY.md`, `MEMORY.md`, `TOOLS.md`, `STATE_MODEL.md`.

Core boundary: Walter manages work and does not perform specialist deliverables. Use subagents for one bounded lane with one inspectable deliverable. Only the Manager creates, redirects, replaces, or retires subagents; children must not spawn agents.

## Working in this repo

Python 3.11+ and Bubblewrap (`/usr/bin/bwrap`) are required. Sandbox execution fails closed if the isolation backend is missing or unusable — never substitute host execution.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q                                 # offline suite, no provider credits
WALTER_LIVE_SMOKE=1 python -m pytest -q -m live     # opt-in, credit-bearing provider smoke
```

There is no lint, format, or typecheck tooling configured; `pytest` (via `[tool.pytest.ini_options]`) is the only verification entrypoint. `tests/test_runtime.py` and `tests/test_adapter.py` use `pytest.importorskip("agents")`, so SDK-dependent coverage silently disappears if the SDK is not installed in the active venv.

Runtime config comes from a gitignored `.env` (see `.env.example`): `OPENROUTER_API_KEY`, `WALTER_MODEL_PROVIDER=openrouter`, `WALTER_MODEL`, `WALTER_WORKER_MODEL`, `OPENROUTER_BASE_URL`. OpenRouter is the only configured provider. Never commit a real key.

## Architecture

- `src/walter/orchestration.py` — deterministic kernel: lifecycle, acceptance, approvals, authority. The model proposes; the kernel authorizes.
- `src/walter/adapter.py` — Agents SDK boundary and Manager/worker tools; `runtime.py` wires `build_walter`, `cli.py` is the `walter` entrypoint.
- The durable Manager's instructions are the repo-root `SYSTEM_PROMPT.md` plus a short operational appendix and the run ID (`DurableController.instructions()`).
- `src/walter/sandbox.py` — fail-closed Bubblewrap isolation for candidate worktrees.
- `src/walter/store.py` / `models.py` — atomic SQLite snapshots, append-only events, durable records.
- `src/walter/readiness.py` — offline self-build readiness fixture.

Two SQLite databases with distinct roles live in gitignored `.local/`: `walter-sessions.db` holds conversation continuity only; `walter-operations.db` is authoritative run/task/artifact/approval state. Clearing a conversation does not erase operational truth.

## Gotchas

- Canonical task states are defined in OPERATING_MODEL.md. Only `ACCEPTED` upstream work satisfies dependencies.
- New CLI runs start with a sentinel completion criterion; the Manager must call `set_completion_criteria` before planning or delegation.
- `walter run resume` is offline and only converts interrupted `DELEGATED`/`RUNNING` work to `FAILED` with `TIMEOUT` evidence; add `--execute` to invoke the model. Only `--execute` needs provider config.
- `--trace-sensitive` is a reserved no-op: provider trace export and sensitive payloads are always disabled.
- `docs/walter-bootstrap-master-blueprint.md` supersedes older bootstrap docs and lifecycle terminology (DEC-001); `docs/IMPLEMENTATION_STATE.md` tracks current verified evidence.
- Target-project artifacts belong in their target repositories, not here, unless the task is to improve Walter itself. Candidate development uses Manager-created worktrees; ordinary grants cannot mutate the live checkout, safety/authority paths, secrets, or control-plane modules.
