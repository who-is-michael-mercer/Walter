# Implementation state

## Overnight Manager V1 — 2026-09-17

Active objective: improve the existing Manager runtime, reliability, and routine context cost.
The user authorizes implementation, bounded OpenRouter experiments (soft $25, hard $40),
feature-branch commits and push; no merge, deployment, security weakening, or unrelated work.
This supersedes the completed bootstrap's historical stop condition below for this build.

Historical build baseline: clean `main` at `fb480e0`; development used an isolated implementation feature branch.
Existing suite: **95 passed, 1 opt-in live test skipped** (13.72 seconds).

| Task | Deliverable | Dependencies | State | Owner |
| --- | --- | --- | --- | --- |
| CTX-01 | Compact active prompts and instruction classification with loading tests | Repository baseline | RUNNING | context_diet |
| RUN-01 | Bounded execution/admission, classified interruption and preserved candidates | Repository baseline | RUNNING | runtime_reliability |
| MODEL-01 | Bounded reproducible routing experiments and measured outcomes | Existing integration and provider availability | RUNNING | model_experiments |
| AUDIT-01 | Independent evidence of remaining context/acceptance/recovery gaps | Repository baseline | ACCEPTED | runtime_audit |
| INPUT-01 | Required-input provenance and transitive stale-evidence invalidation | AUDIT-01 reproduction | RUNNING | input_integrity |
| CTX-02 | Declared accepted input hydration and useful revision feedback | AUDIT-01; CTX-01 interface | PLANNED | Pending assignment |
| QA-01 | Independent review, full verification, coherent commits and handoff | Accepted candidate changes | PLANNED | Walter assigns reviewer |

Acceptance: preserve canonical-state and accepted-only dependency gates; bound attempts and
concurrency; retain useful failure evidence; exercise unhappy paths; reduce actual prompt load;
report live model availability/cost honestly; independently review implementation before acceptance.
MODEL-01 has a $2 soft/$3 hard sub-budget. No other live spending is allocated yet.

AUDIT-01 confirmed three gaps using in-memory diagnostics: artifact-valued required inputs
were omitted from provenance/invalidation and stale downstream acceptance could satisfy completion;
workers/reviewers received input identifiers without resolved values; revision workers received
neither preserved partial results nor corrective feedback. These findings drive INPUT-01/CTX-02.

### MODEL-01: bounded provider comparison

Harness: `python -m walter.model_eval --live` (explicit paid opt-in). Uses Walter's
OpenRouter model/client integration through Agents SDK, two centralized model IDs,
three fixed JSON oracles per model, one request per case. HTTP and SDK retries are
disabled; provider fallback is disabled. Each request permits at most 1,024 output
tokens and 60 seconds. Input fixtures are limited to 4,096 UTF-8 bytes with an
8,192-token conservative input allowance. Provider price ceilings are $5/$20 per
million input/output tokens and zero per-request fees. The six-call plan reserves
$0.36864 before execution, below the $2 soft/$3 hard lane limits. Availability errors
stop the plan; a new invocation starts a new budget and requires separate authorization.

The [official catalog](https://openrouter.ai/api/v1/models) confirmed
`moonshotai/kimi-k3` and `deepseek/deepseek-v4.1-flash`; the completed run's catalog
timestamp was **2026-09-17T17:43:41Z**. Earlier same-day catalog observations listed
Kimi at $3/$15 per million input/output tokens and DeepSeek at $0.15/$0.60, with
time-dependent overrides up to $0.30/$1.20. These are catalog observations, not
guarantees of future price or provider availability. Price ceilings follow the
[provider routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection#max-price).

Completed run evidence supplied by Walter after executing the checked-in harness:

| Model | Case | Accepted | Attempts | Latency (s) | Input/output tokens | Provider-reported cost (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| Kimi K3 | Dependency reasoning | Yes | 1 | 17.086 | 178 / 221 | 0.002654250 |
| Kimi K3 | Exact expression edit | Yes | 1 | 10.681 | 164 / 167 | 0.002061000 |
| Kimi K3 | Gate counterexample review | Yes | 1 | 14.236 | 185 / 213 | 0.002583375 |
| DeepSeek V4.1 Flash | Dependency reasoning | Yes | 1 | 2.499 | 109 / 176 | 0.000121950 |
| DeepSeek V4.1 Flash | Exact expression edit | Yes | 1 | 1.680 | 98 / 99 | 0.000074100 |
| DeepSeek V4.1 Flash | Gate counterexample review | Yes | 1 | 2.340 | 119 / 151 | 0.000108450 |

Provider-reported total for that run: **$0.007603125**, six requests, all six exact
oracles passed. No retry or fallback occurred within the completed run.

An earlier run at 2026-09-17T06:03:20Z made four requests: Kimi passed all three
oracles, then DeepSeek returned HTTP 429 (`RateLimitError`) on its first case and
the harness stopped without retry. Kimi input/output tokens were 175/109, 161/69,
182/181; latencies were 7.119, 2.738, 6.172 seconds; the failed DeepSeek request
took 0.917 seconds. That run did not preserve provider billing: its successful
responses estimate $0.006939 at observed catalog rates, bounded by $0.009770 using
the configured price ceilings; billing for the rejected request is unknown.
The two runs together reserved **$0.6144**, counting a full reserve for the failure.
Known completed-run billing plus the earlier catalog estimate is $0.014542125,
excluding any charge for the rejected request; this is not a verified lane invoice.

Decision: preserve Kimi as the default Manager and select DeepSeek Flash as the
default worker to match the intended cost strategy. `WALTER_MODEL` and
`WALTER_WORKER_MODEL` continue to override defaults independently. The three tiny
fixtures establish JSON formatting and accepted-dependency gate reasoning only.
The expression edit is compared as text and never applied or executed; these
results do not establish repository implementation, tool-use, long-run Manager,
or independent-review competence. The HTTP 429 demonstrates an availability risk.
No model-generated raw response or credential artifact is required in the repository.

Focused verification: `python -m pytest -q tests/test_runtime.py tests/test_model_eval.py`.

## Completed bootstrap history

## Goal GOAL-001

Implement `docs/walter-bootstrap-master-blueprint.md` through milestone 6: a durable,
inspectable orchestration system demonstrated ready for bounded self-development.
Stop before a real autonomous self-development objective or candidate promotion.

Historical bootstrap constraints: work only in this isolated clone on the bootstrap feature branch;
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
