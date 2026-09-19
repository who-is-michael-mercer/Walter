# Failure Recovery

## Executable taxonomy

- `BAD_OUTPUT`
- `MISSING_EVIDENCE`
- `CONSTRAINT_VIOLATION`
- `TASK_AMBIGUITY`
- `DEPENDENCY_FAILURE`
- `TOOL_FAILURE`
- `PROVIDER_FAILURE`
- `TIMEOUT`
- `CAPABILITY_UNAVAILABLE`
- `UNSUPPORTED_CAPABILITY`
- `REPEATED_BAD_OUTPUT`

Operator-facing descriptions may group these, but durable records use the names above.

## Bounded routing

Capture evidence, classify the failure, preserve valid artifacts, then choose the smallest supported correction. Bad output normally receives a targeted revision while the revision limit permits it. Repeated bad output or exhausted revision routes replace/reassess. Provider failure may receive a bounded retry. Ambiguity or dependency failure routes to explicit replan. Tool/capability failures route to repair, block, or escalation rather than bypass.

Worker `blocked` and `needs_revision` outputs are expected result routes, not thrown tool failures. Persist the partial result first, then use `MISSING_EVIDENCE` or `BAD_OUTPUT`; use `CAPABILITY_UNAVAILABLE` when a structured capability request accompanies the result. No route creates an artifact or unlocks downstream work.

If a repository capability request is rejected or setup/linking fails, clean its pending Manager-created workspace and leave the task without the requested authority. An approved request is safe to retry after restart: capability application is idempotent and must either atomically bind the exact profile/workspace and record `escalated`, or make no partial change. Redelegation reuses that workspace with tools derived from the applied profile.

Every recovery decision records actor, failure, action, reason, affected IDs, and evidence. A failure cannot be recovered twice. Attempt, revision, and plan-revision limits prevent loops; reaching a limit requires replacement, blocking, escalation, or a materially different plan.

## Interruption

Reload never assumes an interrupted worker finished. `resume` changes persisted `DELEGATED` and `RUNNING` tasks to `FAILED` with `TIMEOUT` evidence. The Manager must inspect each failure and explicitly recover before delegation can continue.

## Replanning

A replan records its base plan revision, trigger, evidence, additions/removals/reopens, dependency changes, risks, and approval reference when required. Application is atomic and bounded. Reopening accepted work supersedes its accepted artifacts and transitive consumer artifacts so stale evidence cannot remain canonical.

Every model-facing runtime replan is marked approval-required and linked to exact scope `{proposal_id, base_revision}`. The core retains a lower-level no-approval route for trusted programmatic low-impact changes; model output cannot select that route.

Blind identical retries, hidden takeover by the Manager, silent task resurrection, discarded useful evidence, and false completion are prohibited.

## Approval and workspace replacement

Do not supersede an approval while work bound to it is active. Fail the task with evidence, recover it to a safe state, then issue the linked replacement request. Ambiguous schema-v1 bare approval IDs remain blocked until the Manager attaches an exact existing request with `recover_legacy_approval_gate`.

A developer revision never reuses a rejected mutable workspace. After failure/recovery, freeze the old workspace, create a fresh isolated candidate, and call the kernel's checked `replace_workspace` with the expected old ID and reason. Retain the frozen old worktree as inspectable partial evidence; assignment history and the event trail preserve both identities. There is no automatic retention cleanup. Eventual cleanup requires a separate authorized manual or external operation, after evidence-retention needs have been addressed.
