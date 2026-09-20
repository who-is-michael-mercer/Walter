# Quality Assurance Protocol

## Evidence chain

Worker output is always provisional. Acceptance requires evidence bound to the exact candidate content digest and, for workspace work, the frozen workspace fingerprint.

1. The worker submits a structured result and candidate artifact.
2. Trusted validators run every predeclared check.
3. A fresh reviewer evaluates the candidate and criteria when review is required.
4. The Manager records an acceptance decision only after all gates pass.
5. Only the accepted artifact may enter canonical state or unlock dependents.

The author cannot validate or review its own artifact. The reviewer must differ from the author, receives read-only access, and cannot alter or accept the candidate. A development reviewer must actually inspect candidate files. Changed candidate identity makes earlier evidence stale.

Submission is assignment-bound: task, assignment ID, and worker ID must match the current persisted assignment. Candidate action approval is constructed and later rechecked from trusted current workspace/artifact state; model-supplied branch, base, or diff identity is insufficient.

## Trusted checks

The current adapter supports `result_schema`, `compile`, and `pytest`. `result_schema` verifies structured completion and a nonempty deliverable; it is not a claim of substantive quality. `compile` is Python syntax validation over candidate sources. Executable checks run through the isolated sandbox and record argv, return code, stdout, and stderr. A developer candidate must add or modify at least one `test_*.py`/`*_test.py` file; `pytest` validates only the candidate's changed test files inside the isolated sandbox and fails if none are present.

## Review policy

Runtime-planned tasks require independent review; `developer_sandbox` tasks are marked high risk. Review should test every acceptance criterion and use artifact, validation, source/diff, and relevant upstream evidence. Security, safety, permission, and self-modifying work always require independent evaluation.

The Manager checks deliverable existence, scope, criteria, contradictions, provenance, validation results, reviewer independence, and candidate identity. Manager acceptance is necessary but does not replace scoped human promotion approval.

## Rejection

Failed validation or review prevents acceptance. Correction routes through `REVISION_REQUIRED`, replacement, or explicit replan. Default maximum revisions with the same route are two; attempts and replans are separately bounded. Conflicting material judgments require targeted follow-up or adjudication, not averaging.

Adjudication is a design reference only: it is not an implemented mechanism in the
current runtime. Conflicting judgments currently route through targeted follow-up,
revision, replacement, or explicit replan.
