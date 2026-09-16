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
| TASK-001 | Repository reconciliation and implementation map | Blueprint and existing source | ACTIVE | reconcile |
| TASK-002 | Typed kernel, persistence, acceptance and approval invariants | Blueprint and existing contracts | ACTIVE | kernel |
| TASK-003 | Isolated developer workspaces and bounded tools | Blueprint and existing Git clone | ACTIVE | sandbox |
| TASK-004 | Durable SDK/CLI integration | Existing runtime, agreed core interfaces; final acceptance awaits TASK-002/003 | ACTIVE | adapter |
| TASK-005 | Documentation reconciliation and readiness evidence | Accepted implementation interfaces | BLOCKED | unassigned |
| TASK-006 | Independent adversarial review and full verification | Implemented kernel, sandbox and adapter | BLOCKED | unassigned |

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
