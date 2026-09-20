# Candidate Result Packet

> Status: not implemented in the current runtime; retained as design reference.

**Task ID:** TASK-___
**Worker/assignment ID:** ___
**Worker-result status:** `completed` / `blocked` / `needs_revision`

Worker-result status describes the submission only. It is distinct from canonical task state and never means `ACCEPTED`.
The task ID, assignment ID, and worker identity must match the current durable assignment or submission is rejected.

## Summary and candidate deliverable

## Artifact references and changed files

## Evidence / checks performed by worker

Worker checks are evidence only; identify commands and observed results without claiming trusted validation or acceptance.

## Inputs used and provenance

## Facts

## Assumptions / inferences

## Uncertainties and issues

## Additional expertise or capability needed

When requesting capability, provide exactly:

- **Requested capability:** `model_only` / `researcher` / `repo_reader` / `developer_sandbox` / `reviewer`
- **Reason:** why the acceptance criteria cannot be met with the current profile
- **Risk:** concrete exposure introduced by the requested profile

Represent these as the structured `capability_request` payload. A request normally accompanies `blocked`; it preserves partial work but creates no artifact or authority.

## Recommended Manager action

Submit for trusted validation/review, revise, replace, replan, block, or escalate. The worker may not recommend itself as accepted.
