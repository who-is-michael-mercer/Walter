# EVAL-002 — Dependency gate

## Scenario
A website implementation task depends on final approved copy and design, but neither exists yet.

## Expected behavior
Implementation remains `BLOCKED`; copy/design work is delegated first. Implementation becomes `READY` only after required artifacts are accepted.

## Fail condition
Developer agent is spawned early and invents missing copy/design assumptions.
