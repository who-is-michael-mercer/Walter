# Task Packet

**Task ID:** TASK-___
**Assignment ID (filled at delegation):** ___
**Parent goal/run:** GOAL-___ / RUN-___
**Specialist lane:** ___

## Objective

One bounded outcome.

## Required inputs

- Durable input/artifact IDs and references.

## Context and constraints

- Minimum sufficient context.
- Scope, protected boundaries, and non-goals.

## Dependencies

- Upstream task IDs; each must be `ACCEPTED` before readiness.

## Capability and tools

**Profile:** `model_only` / `researcher` / `repo_reader` / `developer_sandbox` / `reviewer`
**Granted tools:** ___
**Approval required:** ___
**Approval category/action/exact scope:** ___
**Forbidden:** agent creation, scope expansion, self-acceptance, ungranted access, external commitment.

If current capability is insufficient, return a structured capability request in the result. Do not attempt the ungranted action.
If the profile is `developer_sandbox`, required trusted checks below must include `compile` or `pytest`. This applies to initial plans, replans, and approved capability changes.

## Deliverable

One inspectable candidate artifact.

## Acceptance criteria

- Measurable criterion.

## Required trusted checks and review

- Checks: `result_schema` / `compile` / `pytest`
- Independent review required: yes/no; rationale.

## Bounds and stop condition

- Attempt/revision/time limits.
- Stop after delivering the candidate or reporting exact evidence-backed blocker.

## Result format

Return the structured fields in `templates/RESULT_PACKET.md`. Worker status is provisional and never means Manager acceptance.
