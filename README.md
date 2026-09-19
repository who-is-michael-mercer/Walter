# Walter

Walter is a standalone Python application built on the OpenAI Agents SDK, with OpenRouter providing model access. Its Manager-controlled orchestration turns a human objective into a durable plan, delegates bounded specialist tasks, validates and reviews candidate outputs, and accepts only evidence-backed artifacts. Run it through the `walter` CLI; no editor integration or custom-agent configuration is required.

> Walter manages work. Walter does not perform specialist deliverables himself.

The executable bootstrap provides:

- a deterministic task graph and lifecycle;
- atomic SQLite operational snapshots and append-only events;
- candidate artifact provenance, validation, review, and Manager acceptance;
- bounded failure recovery and explicit replanning;
- enforceable capability profiles, typed worker capability requests, and scoped human approvals;
- isolated Git candidate worktrees with fail-closed Bubblewrap execution;
- an Agents SDK adapter in which models propose actions and the kernel authorizes them.

The canonical task states are `PLANNED`, `READY`, `DELEGATED`, `RUNNING`, `SUBMITTED`, `REVIEWING`, `REVISION_REQUIRED`, `ACCEPTED`, `REPLACED`, `BLOCKED`, `FAILED`, and `CANCELLED`. Only `ACCEPTED` upstream work satisfies dependencies.

## Install and configure

Walter requires Python 3.11+ and Bubblewrap (`/usr/bin/bwrap`) for isolated command execution.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Set an OpenRouter key in the environment or a gitignored `.env`:

```text
OPENROUTER_API_KEY=your_openrouter_key_here
WALTER_MODEL_PROVIDER=openrouter
WALTER_MODEL=moonshotai/kimi-k3
WALTER_WORKER_MODEL=deepseek/deepseek-v4.1-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

OpenRouter is the only configured provider. The defaults are Kimi K3 for the Manager and DeepSeek V4.1 Flash for specialists, including reviewers; the two environment overrides are independent. Tiny live comparisons and their limits are recorded in `docs/IMPLEMENTATION_STATE.md`. `researcher` maps to the Agents SDK hosted `WebSearchTool`; compatibility through OpenRouter's chat-completions endpoint is provider-dependent and is not established by the offline suite. Research must block honestly if a live provider rejects that hosted tool. Live provider tests are opt-in.

Provider trace export and sensitive trace payloads remain disabled. The accepted `--trace-sensitive` option is a reserved compatibility no-op; CLI output labels workflow identifiers as `Local trace ID (provider export disabled)`.

## Use

Interactive and one-shot goals use the durable control plane:

```bash
walter
walter --session project-a
walter "Implement a bounded objective"
```

Conversation continuity lives in `.local/walter-sessions.db`. Authoritative run/task/artifact/approval state lives separately in `.local/walter-operations.db`; clearing a conversation does not erase operational truth.

Both Manager entry points load the compact `SYSTEM_PROMPT.md` kernel; detailed policy is available through the fixed-file `read_reference` tool. Durable specialists receive only their task packet, resolved declared inputs and accepted upstream artifacts, plus applicable revision evidence. The context envelope rejects stale inputs and oversized content rather than silently omitting evidence. Whole run history is not copied into specialist context.

Inspect and operate durable runs:

```bash
walter run list
walter run inspect RUN_ID
walter run events RUN_ID
walter run resume RUN_ID
walter run resume RUN_ID --execute
walter run approve RUN_ID APPROVAL_ID --reason "Reviewed exact scope"
walter run approve RUN_ID APPROVAL_ID --deny --reason "Scope rejected"
walter run readiness-demo
```

`resume` is guarded and offline by default: it reloads durable state and marks interrupted `DELEGATED` and `RUNNING` assignments `FAILED` with `TIMEOUT` evidence for explicit recovery, without invoking a model. Add `--execute` only when you intend the configured Manager model to continue the recovered run. `approve` records the local OS username/UID as operator identity; this is a local audit label, not strong authentication. Approval does not execute merge, push, deploy, or promotion.

New CLI runs begin with a sentinel criterion that cannot satisfy completion. The Manager must call `set_completion_criteria` with distinct measurable criteria before planning or delegation. Provider configuration is validated before a new provider-backed run is created and before `resume --execute`; offline resume does not require provider configuration. Sessions/controllers/stores are closed on all normal and error paths.

Operational schema v2 adds typed approval lifecycles and gates. Opening a v1 database migrates snapshots transactionally and retains exact source snapshots in `schema_migration_backups`; ambiguous legacy task approval IDs remain blocked until the Manager calls `recover_legacy_approval_gate` with an exact typed request.

A worker that returns `blocked` or `needs_revision` produces a durable provisional result, not a candidate artifact. It cannot unlock dependencies and is classified/recovered without being mislabeled as a tool failure. A typed capability request carries requested profile, reason, and risk through `pending`, `approved`, `denied`, and `escalated` states. Repository-read and developer requests bind exact Manager-created workspaces into the approval scope. Applying an approved request atomically and idempotently updates the task capability/workspace and records `escalated`; rejection grants nothing and cleans the pending workspace. Redelegation reuses the approved workspace with read-only tools for `repo_reader` or bounded write/check tools for `developer_sandbox`. Developer tasks must declare `compile`, `unittest`, or `pytest` at planning, replanning, and capability change. Model-facing replans are likewise always persisted behind exact human approval, even though trusted programmatic callers may use the low-level core for authorized low-impact replans.

Recovered developer revisions receive a fresh candidate workspace. The previous workspace is frozen and retained as inspectable partial evidence in assignment history. There is no automatic retention cleanup; eventual removal requires a separate authorized manual or external cleanup step.

Run verification with:

```bash
python -m pytest -q
WALTER_LIVE_SMOKE=1 python -m pytest -q -m live
```

The readiness demo is a harmless offline fixture. It exercises the real isolation backend, candidate work, validation, independent review, Manager acceptance, durable reload, and a trusted current-candidate promotion request, then stops with that human decision pending. Passing it demonstrates bootstrap self-build readiness; it does not authorize real self-development or promotion.

## Repository map

- `src/walter/` — durable models, store, kernel, sandbox, SDK adapter, runtime, and CLI.
- `SYSTEM_PROMPT.md` — Manager doctrine loaded by the runtime.
- `OPERATING_MODEL.md`, `TASK_PROTOCOL.md`, `STATE_MODEL.md` — executable orchestration semantics.
- `PERMISSIONS.md`, `TOOLS.md`, `QA_PROTOCOL.md`, `FAILURE_RECOVERY.md` — authority, capability, evidence, and recovery rules.
- `docs/walter-bootstrap-master-blueprint.md` — primary bootstrap specification.
- `docs/IMPLEMENTATION_STATE.md` — current implementation graph and verified evidence.
- `templates/`, `runbooks/`, `evals/`, `prompts/` — operational support material.

Target-project artifacts belong in their target repositories. Candidate development uses Manager-created worktrees. Ordinary grants cannot mutate Walter's live checkout, safety/authority paths, secrets, or control-plane modules; an exact one-use human-approved safety grant is a separate authority path.
