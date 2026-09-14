# Operations Runbook

## Start of a new goal

1. Create goal ID.
2. Record desired outcome and constraints.
3. Determine whether domain-scoping is required.
4. Build initial dependency graph.
5. Define acceptance criteria for first executable tasks.
6. Mark task states.
7. Spawn workers only for `READY` tasks.

## During execution

- maintain canonical state;
- enforce concurrency cap;
- review worker results;
- apply reviewer threshold;
- record decisions that materially change execution;
- replan when new dependencies emerge;
- avoid unnecessary human interruption.

## End of goal

1. Confirm all required deliverables accepted.
2. Confirm required QA passed.
3. Confirm no unresolved critical dependency.
4. Produce final outcome report.
5. Retire remaining temporary workers.
6. Perform lightweight retrospective for major goals.
7. Promote durable lessons only when broadly useful.

## Emergency stop / cancellation

Freeze new delegation, stop irrelevant work where supported, preserve accepted and useful partial artifacts, record state, and report what remains.
