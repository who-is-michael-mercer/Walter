# Changelog

## Unreleased

### Added

- Durable orchestration models, atomic SQLite operational state/events, artifact lineage, scoped approvals, bounded recovery/replanning, and guarded run inspection/resume/approval commands.
- Enforceable capability profiles, isolated candidate worktrees, fail-closed Bubblewrap checks, trusted validation, independent review, and an offline self-build-readiness fixture that stops at human promotion approval.
- Schema-v2 approval lifecycle/gates with transactional v1 backups and explicit legacy-gate recovery; assignment-bound submissions; audited revision workspaces; trusted current-candidate approval scope; and one-use, exactly scoped safety-boundary grants.
- Assignment-bound typed capability requests with partial-result preservation, exact Manager-created repository workspaces, atomic/idempotent restart-safe application, cleanup on rejection, profile-correct redelegation, and mandatory executable checks for developer plans/replans/changes.
- Stale workspace-grant reconciliation that closes grants whose signed manifest no longer matches the host environment.
- Forward-compatible durable snapshot loading that prunes unknown fields and emits clear diagnostics instead of failing.
- Env-configurable per-run usage budget (`WALTER_MAX_MODEL_CALLS`, `WALTER_MAX_INPUT_TOKENS`, `WALTER_MAX_OUTPUT_TOKENS`, `WALTER_MAX_TOTAL_TOKENS`) with clean exhaustion reporting.
- Live end-to-end verification on 2026-09-20: a model-driven run planned, delegated, validated, independently reviewed, accepted, and completed within its token budget.

### Changed

- Scoped developer validation to the candidate's changed/added test files: `pytest` now runs only those files inside the isolated sandbox and requires the candidate to add or modify at least one test file; removed the non-functional `unittest` check.
- Adopted the Master Blueprint's canonical task lifecycle and acceptance-only dependency semantics throughout executable doctrine and templates.
- Separated Agents SDK conversation sessions from authoritative operational state and documented the current OpenRouter hosted-web limitation.
- Guarded new CLI runs with a completion-criteria sentinel, provider preflight, deterministic resource closure, and OS-derived local operator audit identity.
- Kept the legacy trace-sensitive option as an honest no-op: provider trace export and sensitive payloads remain disabled, and displayed workflow identifiers are explicitly local.
- Made the durable store safe across Agents SDK tool-dispatch threads.
- Fixed CLI session cleanup and Manager output surfacing.

### Safety boundary

- Self-build readiness does not authorize real autonomous self-development, merge, push, deploy, or candidate promotion.

## 1.0.1 — 2026-09-14

### Changed

- Renamed the Manager identity from `Agent Manager` to **Walter**.
- Updated Codex entry instructions, charter, system prompt, and README to use Walter as the agent/product name while retaining `Manager` as the functional role.
- Standardized the recommended local installation path as `~/Projects/Walter`.

## 1.0.0 — 2026-09-14

Initial v1 specification.

### Includes

- general-purpose Manager charter;
- high-autonomy exception-based escalation;
- centralized worker creation;
- one-agent-one-lane delegation;
- dependency-aware execution graph;
- minimum-sufficient context and least-privilege tools;
- risk-based independent QA;
- failure classification and recovery;
- canonical state/memory promotion rules;
- worker, reviewer, scoping, and adjudication prompts;
- task/result/state/decision/failure templates;
- initial orchestration evaluation suite.
