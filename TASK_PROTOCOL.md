# Task Protocol

## Stable identifiers

Use stable IDs for goals, workstreams, tasks, agents, artifacts, gates, and decisions.

Suggested forms:

- `GOAL-001`
- `WS-001`
- `TASK-001`
- `AGENT-001`
- `ART-001`
- `GATE-001`
- `DEC-001`

## Task readiness

A task may become `READY` only when:

- all required upstream artifacts are accepted;
- required access is available;
- constraints are known enough to execute safely;
- acceptance criteria are defined;
- no unresolved gate blocks execution.

## Delegation

Every delegated task uses `templates/TASK_PACKET.md`.

## Worker result

Workers return `templates/RESULT_PACKET.md` or an equivalent structured payload.

## Completion rule

A task moves to `COMPLETE` only after the Manager verifies the deliverable against acceptance criteria and any required reviewer passes it.

## Scope discovery

Newly discovered required work is inserted into the graph with dependencies. Optional enhancements are placed in backlog unless needed to meet acceptance criteria.

## Cancellation/change

When the human changes or cancels a goal:

1. stop spawning now-irrelevant work;
2. stop or retire irrelevant active tasks where possible;
3. preserve useful artifacts;
4. update canonical state;
5. replan from the new instruction.
