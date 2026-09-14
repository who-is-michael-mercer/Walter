# Memory and Canonical State

## Principle

The Manager owns canonical project state. Worker output is provisional until accepted.

## Persist

Persist durable information that materially improves future execution:

- accepted project decisions;
- accepted deliverables and their references;
- task graph state and dependencies;
- stable constraints;
- user-approved preferences relevant to work;
- known issues and blockers;
- audit history needed to reconstruct important decisions;
- lessons from major retrospectives when reusable.

## Do not automatically persist

- worker scratch reasoning;
- rejected deliverables;
- transient task chatter;
- secrets, passwords, tokens, or credentials;
- unverified assumptions;
- irrelevant personal information.

## Promotion rule

A worker's output becomes canonical only after the Manager accepts it against the task's acceptance criteria and any required independent review passes.

## Conflict order

When information conflicts, prefer:

1. explicit current human instruction;
2. current authoritative source;
3. accepted recent decision;
4. older canonical state;
5. worker assumption.

Material conflicts are resolved explicitly; they are not silently blended.

## Worker memory

Worker memory is ephemeral by default. Reuse continuity only when the same specialist lane benefits from retained context and doing so does not create stale-state risk.
