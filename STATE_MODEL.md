# State Model

Walter's authoritative operational state is stored independently of Agents SDK conversation sessions.

## Durable entities

- `Run`: objective, constraints, status, plan, tasks, artifacts, accepted artifacts, inputs, decisions, failures/recoveries, approvals, replans, issues, completion result, schema/version, and event cursor.
- `WorkPlan`: structured completion criteria, task IDs, assumptions, risks, revision history, and bounded replan count.
- `TaskNode`: task packet, capability, workspace, checks/review policy, canonical status, limits/counters, assignment history, artifacts, result, blockers, and approval references.
- `Artifact`: producer/run/task, content digest, workspace fingerprint, version/predecessor, input lineage, validations, reviews, and candidate/accepted/superseded status.
- `Decision`: actor, action, reason, affected IDs, evidence, and time. Acceptance and recovery specialize this record.
- `ApprovalRequest` and `ApprovalDecision`: exact action/scope digest, category/target/risk/artifact references, lifecycle status (`pending`, `approved`, `rejected`, `superseded`), and one immutable human decision.
- `CapabilityRequest`: run/task/assignment/worker identity, requested profile, reason, risk, linked approval, optional exact Manager-created workspace, and lifecycle status (`pending`, `approved`, `denied`, `escalated`). Runtime application atomically and idempotently binds profile/workspace before recording `escalated`.
- `Event`: ordered run-scoped audit record for every mutation.
- `WorkspaceGrant`: repository/worktree/base identity, worker/task/run/author binding, command templates, read-only/safety policy, and lifecycle. `inspect_grant` returns a validated immutable copy for trusted Manager scope construction.

## Storage invariants

`.local/walter-operations.db` uses schema v2 with atomic versioned run snapshots plus append-only ordered events. Optimistic concurrency rejects stale mutations. Snapshot/run identity, schema, event payload identity/sequence, and cursor are checked on load.

Opening schema v1 performs a transactional v1→v2 transformation and stores each exact source snapshot in `schema_migration_backups`. Well-formed bare approval IDs become typed exact gates without changing the event timeline. Missing or ambiguous legacy approval references remain in `approval_ids`, force the task to `BLOCKED`, and require explicit `recover_legacy_approval_gate`; migration never guesses their authority.

`.local/walter-sessions.db` contains conversation continuity only. It cannot prove acceptance, approval, artifact identity, or task state and is never the operational authority.

Candidate evidence is immutable by identity: later workspace or content changes invalidate earlier validation/review and require a new artifact or evidence. Accepted upstream invalidation supersedes transitive consumer artifacts and removes them from canonical accepted state.

Provisional `blocked`/`needs_revision` results live on the task and in assignment events but do not enter the artifact registry. Capability requests are separate durable objects; their partial result remains recoverable while dependency state remains locked.

Approval supersession preserves the prior request and links its replacement. If a superseded request is bound to `DELEGATED`, `RUNNING`, `SUBMITTED`, or `REVIEWING` work, the Manager must fail and recover that task before replacement. Workspace replacement is likewise an audited revision event, never an in-place rebind.

Use `walter run inspect RUN_ID` and `walter run events RUN_ID` for the machine-readable snapshot and timeline. `docs/IMPLEMENTATION_STATE.md` is project implementation tracking, not live runtime state.
