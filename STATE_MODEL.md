# State Model

## Canonical entities

### Goal
- ID
- desired outcome
- status
- constraints
- priority
- completion criteria

### Workstream
- ID
- parent goal
- purpose
- task IDs

### Task
- ID
- workstream
- state
- priority
- dependencies
- required inputs
- assigned agent
- acceptance criteria
- artifact IDs
- revision count

### Agent
- ID
- role/lane
- task ID
- tool grants
- status
- creation time
- retirement state

### Artifact
- ID
- producer task
- location/reference
- version
- acceptance status
- reviewer result

### Decision
- ID
- context
- options
- chosen action
- reason
- consequences

### Gate
- ID
- prerequisite artifacts/tasks
- acceptance condition
- downstream tasks unlocked

## Auditability

Maintain enough history to reconstruct:

- what the human requested;
- how the goal was decomposed;
- which worker owned each task;
- what was produced;
- what was accepted or rejected;
- why revisions/replacements occurred;
- how the plan changed;
- what verification was performed.

## Snapshot

Use `templates/CURRENT_STATE.md` for a human-readable current-state snapshot.
