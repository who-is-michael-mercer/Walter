# Operating Model

## Control loop

Walter translates each objective into:

`Outcome → completion criteria → bounded tasks → dependencies → capabilities/checks → execution → validation/review → Manager acceptance`.

The Manager owns the run. Specialists produce provisional artifacts. Deterministic code owns legal transitions, readiness, persistence, limits, approval scope, and completion.

## Canonical task lifecycle

- `PLANNED` — defined but not yet eligible.
- `READY` — every dependency is `ACCEPTED`, inputs and capabilities exist, criteria/checks are declared, and no gate blocks execution.
- `DELEGATED` — assigned to one temporary worker.
- `RUNNING` — worker execution began.
- `SUBMITTED` — a candidate artifact exists.
- `REVIEWING` — validation or independent review is in progress/recorded.
- `REVISION_REQUIRED` — candidate rejected with corrective direction.
- `ACCEPTED` — Manager accepted evidence-backed work; only this state unlocks dependents.
- `REPLACED` — worker/candidate route replaced after reassessment.
- `BLOCKED` — a known condition prevents execution.
- `FAILED` — execution failed and requires classified recovery.
- `CANCELLED` — plan or human direction invalidated the task.

Legacy prose terms map only as follows: `ACTIVE` ≈ `DELEGATED`/`RUNNING`; `REVIEW` ≈ `SUBMITTED`/`REVIEWING`; `REVISION` ≈ `REVISION_REQUIRED`; `COMPLETE` ≈ `ACCEPTED`. New records and executable interfaces use only canonical names.

## Planning and execution

Decompose by inspectable deliverable, stop at one specialist lane, and create only workers whose required inputs exist. Use progressive elaboration for blocked downstream work. Parallelize independent `READY` tasks only when workspaces and writes cannot conflict.

Each task declares required inputs, dependencies, capability profile, trusted checks, review policy, attempt/revision limits, acceptance criteria, and stop condition. A result is accepted for submission only from the current assignment ID and worker. Assignment history and candidate lineage remain durable.

Developer revision is an explicit lifecycle: reject through classified failure, recover to a safe retry state, create a fresh candidate, atomically record `workspace.replaced`, then clean the old workspace. Silent rebinding is forbidden.

A worker may return `blocked` or `needs_revision` with useful partial work. Walter persists that assignment-bound result, records no candidate artifact, keeps dependents locked, classifies the cause (`MISSING_EVIDENCE`, `BAD_OUTPUT`, or `CAPABILITY_UNAVAILABLE` as appropriate), and recovers explicitly. Ordinary provisional results therefore never become generic `TOOL_FAILURE` records.

Capability escalation is typed and durable: `pending` request → exact scoped human decision → `approved` or `denied` → profile application → `escalated`. `approved` means the decision passed but the capability is not yet durable. Runtime application atomically and idempotently verifies the exact approval, updates task profile/workspace, and closes as `escalated`, so restart/retry cannot create a second change. Repository-read and developer requests precreate an exact Manager-owned workspace, clean it if rejected or setup fails, and reuse it after approval. Redelegation exposes that workspace read-only to `repo_reader` and writable only through bounded developer tools to `developer_sandbox`. Developer tasks require a declared `compile` or `pytest` check when planned, replanned, or changed to that profile. A developer candidate must add or modify at least one `test_*.py`/`*_test.py` file; `pytest` validates only the candidate's changed test files inside the isolated sandbox and fails if none are present.

Every model-facing replan proposal is conservatively approval-gated. Trusted programmatic callers may still apply low-impact proposals directly through the core when they have independently established authority; that core facility is not delegated to the model.

## Acceptance authority

Worker submission is candidate evidence. Trusted validators record check results against the exact artifact digest/workspace fingerprint. A fresh reviewer is distinct from the author and cannot modify or accept the candidate. The Manager may accept only after required validations and reviews pass. The human retains final authority over consequential promotion.

## Persistence and interruption

Conversation sessions and operational state are separate. Ordered events and atomic run snapshots permit reload without reconstructing truth from chat. On resume, interrupted `DELEGATED` and `RUNNING` assignments become `FAILED` with recorded `TIMEOUT` evidence; recovery must be explicit before reassignment.

## Self-build boundary

Self-build readiness means Walter has demonstrated a harmless offline candidate flow through scoped promotion-request creation. It does not authorize a real self-development objective, merge, push, deploy, or promotion.
