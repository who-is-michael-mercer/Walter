# Task Protocol

## Stable identity and packet

Every run, task, assignment, artifact, decision, failure, replan, workspace, and approval has a durable ID. A task packet supplies one objective, required inputs, constraints, dependencies, acceptance criteria, deliverable, and stop condition. Runtime metadata adds capability, checks, risk/review policy, and bounded attempt/revision counts.

## Readiness

A task becomes `READY` only when:

- all dependency tasks are `ACCEPTED`;
- every required input is registered;
- acceptance criteria and trusted checks are declared;
- its capability is available;
- no unresolved gate or approval blocks execution.

Submission never satisfies a dependency. Reopening or invalidating accepted upstream work supersedes affected artifacts and returns transitive consumers to non-executable states.

## Execution and evidence

The canonical path is:

`PLANNED → READY → DELEGATED → RUNNING → SUBMITTED → REVIEWING → ACCEPTED`.

Rejection may route `REVIEWING → REVISION_REQUIRED → DELEGATED`; classified failure may route to retry, revision, replacement, replan, blocking, or escalation within configured limits. Illegal transitions fail atomically and emit no partial mutation.

A submitted result is provisional and must name the current assignment ID and worker. It creates a versioned artifact with producer, inputs, digest, workspace fingerprint when applicable, and predecessor lineage. Validation and review evidence must bind to that exact identity. Manager acceptance is a separate recorded decision.

`blocked` and `needs_revision` are provisional-result routes, not submissions. Persist useful deliverable/evidence against the active assignment, create no artifact, unlock no dependency, then classify and recover. If `capability_request` is present it must contain requested profile, reason, and risk; it remains untrusted until the Manager links exact approval and applies the durable change.

Repository capability escalation binds the approval to an exact Manager-created workspace. Application is atomic and idempotent: it verifies the durable request and human decision, changes the task profile/workspace, and records `escalated` in one mutation. Rejected pending workspaces are cleaned. Subsequent delegation reuses the approved identity with read-only tools for `repo_reader` or bounded write/check tools for `developer_sandbox`. A developer task must include at least one of `compile`, `unittest`, or `pytest`, whether introduced by initial plan, replan, or capability change.

## Change and completion

Required discovered work is added through an explicit replan; optional work remains outside the required graph. Replans preserve base revision, trigger, evidence, changes, risks, and approval reference, and stop at the configured limit. Every model-facing runtime replan requires exact human approval; only trusted low-level programmatic callers may exercise the core's low-impact no-approval path.

A run completes only when the Manager has replaced the CLI sentinel with measurable criteria, all required tasks are `ACCEPTED`, every criterion cites accepted artifact IDs, and no required pending approval or issue remains. Human cancellation stops irrelevant delegation while preserving history and useful artifacts.
