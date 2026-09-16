# Bootstrap implementation state

## Goal GOAL-001

Implement `docs/walter-bootstrap-master-blueprint.md` through milestone 6: a durable,
inspectable orchestration system demonstrated ready for bounded self-development.
Stop before a real autonomous self-development objective or candidate promotion.

Constraints: work only in this isolated clone on `codex/master-blueprint-build`;
preserve the Python / Agents SDK / OpenRouter foundation; use specialist workers;
commit verified milestones; do not merge, push, or access another local checkout.

## Execution graph

| Task | Deliverable | Dependencies | State | Owner |
| --- | --- | --- | --- | --- |
| TASK-001 | Repository reconciliation and implementation map | Blueprint and existing source | ACCEPTED | reconcile |
| TASK-002 | Typed kernel, persistence, acceptance and approval invariants | Blueprint and existing contracts | ACCEPTED | kernel |
| TASK-003 | Isolated developer workspaces and bounded tools | Blueprint and existing Git clone | ACCEPTED | sandbox |
| TASK-004 | Durable SDK/CLI integration | Existing runtime, agreed core interfaces; final acceptance awaits TASK-002/003 | ACCEPTED | adapter |
| TASK-004A | Offline self-build readiness fixture and scoped approval stop | TASK-002/003/004 executable APIs | ACCEPTED | adapter |
| TASK-005 | Documentation reconciliation and readiness evidence | Accepted implementation interfaces | ACCEPTED | docs |
| TASK-006 | Independent adversarial review and full verification | Implemented kernel, sandbox and adapter | ACCEPTED | reviewer |

## Acceptance gates

- Deterministic lifecycle, accepted-only dependencies, bounded recovery and explicit replans.
- Atomic durable operational state/events, provenance, approvals and restart behavior.
- Enforced capabilities, useful isolated development, escape prevention and protected live checkout.
- Actual validation and independent review precede Manager acceptance.
- Scoped human promotion approval; no autonomous merge/push/deploy.
- Default CLI uses the control plane; provider compatibility retained; offline tests and fixture demonstration pass.
- Documentation matches executable behavior, independent review findings resolved, logical commits recorded.

## Decisions

- DEC-001: The Master Blueprint supersedes older bootstrap documents and lifecycle terminology.
- DEC-002: Extend existing runtime; use a separate SQLite operational store, retaining conversation sessions.
- DEC-003: Process isolation must fail closed if its backend is unavailable; working-directory restrictions alone are insufficient.

## Verification and known issues

Initial inspection: clean implementation branch at `bf6f2c7`; only contracts, provider/runtime,
CLI and baseline tests currently exist. System Python lacks the Agents SDK; TASK-002 owns
creating a clone-local test environment. No live provider calls are required for bootstrap verification.

TASK-001 accepted: reconciliation covers all seven bootstrap milestones and identifies reusable
provider helpers/contracts, stale lifecycle/capability documentation, required durable CLI wiring,
and isolation risks. Bubblewrap is installed; executable namespace support remains to be tested.
Independent review must examine immutable evidence binding, upstream invalidation, restart handling,
approval authority and candidate process isolation in addition to ordinary successful workflows.

TASK-003 received independent PASS after two revision cycles and is accepted. The sandbox verifies
signed grants/worktree identity, path-aware secret exclusion, complete candidate fingerprints/diffs,
template-bound execution with immutable dependencies and resource limits, default safety-path denial,
and one-use exact core-approved safety grants. The real isolation/readiness path passed.

TASK-002, TASK-004 and TASK-004A received independent PASS results and are accepted. Current evidence is
95 passing offline tests with one explicitly opt-in live provider smoke test skipped. Implemented hardening
includes schema-v2 transactional
migration/backups and legacy-gate recovery; approval lifecycle/supersession; assignment-bound submission;
audited revision workspace replacement; completion-criteria sentinel; trusted current-candidate action
scope; OS-derived local operator attribution; provider preflight; and resource closure.

TASK-005 received independent PASS after documentation/runtime consistency checks and is accepted.
Doctrine, protocols, templates, CLI/runbooks and changelog match the reviewed interfaces and safety
boundaries.

TASK-006 received independent PASS after the final whole-blueprint audit. The final evidence is 95 passing
offline tests, one explicitly opt-in live provider test skipped, a passing real Bubblewrap readiness path,
clean CLI/help and diff checks, and clean scans for external-checkout dependencies, credentials, candidate
worktree residue, and promotion mechanisms. Milestones 0–6 map to executable models, APIs, events, tests,
and current documentation. The bootstrap ends at readiness; no real autonomous self-development or
candidate promotion was performed or authorized.

TASK-006 audit fixes add assignment-bound typed capability requests and expected routing for provisional
`blocked`/`needs_revision` results; exact Manager-created workspaces for repository-reader and developer
escalations; atomic, idempotent, restart-safe capability application with rejection cleanup and
profile-correct redelegation; executable-check enforcement for developer planning/replanning/change; and
exact human gates for every model-facing replan. These fixes are implemented and covered by the current
test evidence and were accepted by the final whole-blueprint audit.
