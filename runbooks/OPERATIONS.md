# Operations Runbook

## Start and inspect

Configure OpenRouter, then start an interactive or one-shot goal with `walter`. The CLI creates a durable run in `.local/walter-operations.db`; an optional Agents SDK conversation session remains in `.local/walter-sessions.db`.

```bash
walter "OBJECTIVE"
walter run list
walter run inspect RUN_ID
walter run events RUN_ID
```

New CLI runs contain a sentinel completion criterion. The Manager must replace it with distinct measurable criteria through `set_completion_criteria` before planning or delegation. Confirm bounded task packets, accepted-only dependencies, declared capability/checks, and first `READY` tasks.

Provider configuration is checked before creating a new provider-backed run and before `resume --execute`. Offline resume performs only deterministic durable recovery and does not require provider configuration. Controllers, SQLite stores, and conversation sessions close on success and error paths; an unexpected abandoned resource is an operational defect, not an implicit durable run.

## Operate

The normal sequence is plan → delegate → submit → validate → independent review → Manager accept. Inspect durable state rather than inferring it from chat. Treat failures through classification and bounded recovery; mutate the graph only through explicit replans.

Conversation `:clear` does not clear operational state. After interruption:

```bash
walter run resume RUN_ID
```

Resume records interrupted `DELEGATED` and `RUNNING` work as `FAILED` with `TIMEOUT` evidence and requires explicit recovery. It never silently reruns an assignment.

The default resume command is offline and only applies deterministic recovery. Use `walter run resume RUN_ID --execute` when provider-backed Manager continuation is intended.

## Approval stop

Inspect the request and its exact scope in the run before deciding:

```bash
walter run approve RUN_ID APPROVAL_ID --reason "Reviewed exact action and scope"
walter run approve RUN_ID APPROVAL_ID --deny --reason "Reason for rejection"
```

The CLI records `local-os:<username>:uid:<uid>` from the current OS session and accepts no caller-supplied identity. Treat this as local single-user audit attribution, not strong authentication. A recorded approval does not execute the proposed action. Merge, push, deploy, external communication, deletion, permission change, and promotion require a separate mechanism operating on the exact approved scope.

For candidate actions, use the dedicated request path so branch, base revision, artifact/content identity, workspace fingerprint, diff digest, and target come from trusted current state. Authorization recomputes that scope. If material state changes, request a replacement approval. Fail/recover any actively bound task before superseding its approval.

## Schema migration and legacy gates

Opening a schema-v1 operational database migrates it transactionally to v2. Confirm a source row exists in `schema_migration_backups` for each migrated run and inspect blocked tasks for unresolved bare `approval_ids`. Repair one only by creating/locating the intended exact typed request and invoking `recover_legacy_approval_gate`; never infer missing scope from conversation history.

Developer revisions require failure classification/recovery, a new candidate workspace, audited `workspace.replaced`, and old-worktree cleanup. Use validated `inspect_grant` output for trusted branch/base scope; do not read private workspace internals.

For an assignment-bound capability request, inspect requested profile, reason, risk, task, assignment, and worker before invoking `request_capability_change`. Repository-read and developer requests create an exact Manager-owned workspace and include its ID in human approval scope. Developer tasks must already declare `compile` or `pytest`, including when introduced through replan or capability change. After a human decision, `apply_capability_change` denies and cleans a rejected workspace or atomically/idempotently binds the approved profile/workspace and records `escalated`. It is safe to retry after restart. Redelegation reuses that workspace read-only for `repo_reader` and with bounded write/check tools for `developer_sandbox`.

All model-facing replans stop at an exact human approval for `{proposal_id, base_revision}` before `apply_replan`; model assertions that a change is low impact do not bypass this gate. Only trusted programmatic callers of the lower-level core may apply an independently authorized low-impact replan without that model-facing gate.

## Self-build readiness and verification

```bash
python -m pytest -q
walter run readiness-demo
```

The demo has passed with the real local isolation backend. It preserves events/artifacts across reload, proves useful isolated development and escape/network denial, binds validation/review to the candidate, obtains Manager acceptance, creates a trusted current-candidate promotion request, and stops with human approval pending. It establishes readiness only.

If Bubblewrap is missing or unusable, sandbox commands fail closed. Install/fix the isolation backend and rerun; never substitute host execution.
