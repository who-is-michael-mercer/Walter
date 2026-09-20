# Implementation state

Current state of executable `main` (HEAD `c78f8f1`). This document replaces the
earlier bootstrap snapshot; it describes what the runtime actually does today and
where it is still incomplete.

## Verified current capabilities

- **Deterministic 12-state kernel.** Lifecycle across `PLANNED`, `READY`,
  `DELEGATED`, `RUNNING`, `SUBMITTED`, `REVIEWING`, `REVISION_REQUIRED`,
  `ACCEPTED`, `REPLACED`, `BLOCKED`, `FAILED`, and `CANCELLED`; accepted-only
  dependency satisfaction; artifact provenance and lineage validation; typed,
  scoped approvals; capability escalation; bounded recovery and explicit replan;
  and a completion gate that a new run cannot satisfy with its sentinel criterion.
- **Durable store.** Operational schema v2 with atomic snapshots and append-only
  events, optimistic concurrency, transactional v1→v2 migration with retained
  backups, forward-compatible snapshot loading that prunes unknown fields with a
  warning, and thread safety across Agents SDK tool dispatch.
- **Fail-closed Bubblewrap sandbox.** Isolation fails closed if the backend is
  missing or unusable. Signed grant manifests with stale-grant reconciliation,
  a path-aware secret policy, per-task candidate fingerprints and diffs, and
  template-bound commands with resource limits.
- **Agents SDK adapter.** Manager tools, doctrine loading from `SYSTEM_PROMPT.md`,
  and worker/reviewer invocation using the configured worker model.
- **OpenRouter runtime.** OpenRouter is the configured provider, with an
  env-configurable per-run usage budget.

## Verified evidence

- Offline suite: `170 passed, 1 skipped`; the skip is the opt-in live provider smoke.
- Readiness demo passes against real Bubblewrap.
- Live provider smoke passes (2026-09-20).
- One live model-driven end-to-end run completed on 2026-09-20 (run
  `1b6affd4233446de9093d6c4a92b8c6c`): the Manager planned, delegated a real
  worker, trusted validation passed, an independent model review passed, the
  Manager accepted, and the run completed. The run used 16 model calls,
  ~299k tokens, and ~$0.38, within its 300k-token budget.
- Researcher probe (2026-09-20): the SDK hosted `WebSearchTool` is rejected by
  OpenRouter chat completions (`UserError: Hosted tools are not supported`);
  the durable path classified the failure honestly as `TOOL_FAILURE`.
- First real external-repository run (2026-09-20, run
  `04976c30a16c4b82aefa5a9da1894d59`, DeepSeek/Qwen workers): did not complete;
  blocked honestly with attempts exhausted after three worker failures.
  Full findings in `docs/first-real-run-gap-report.md`.
- Eval runner (`evals/runner.py`): EVAL-001/002/003 pass offline against the
  durable runtime (3/3).

## Known gaps and limitations

- Only OpenRouter is supported as a provider.
- The `researcher` profile is unusable with the configured provider (hosted
  `WebSearchTool` rejected by chat completions; verified 2026-09-20).
- All six findings from `docs/first-real-run-gap-report.md` are resolved:
  trusted input registration plus plan-time validation; precise delegation-gate
  errors; capability/check-preserving replan add-path; configurable worker turn
  budget (`WALTER_WORKER_MAX_TURNS`, default 24); compact tool receipts with
  `inspect_run` as the full-truth read; placeholder API key rejected at
  configuration time.
- Usage budgets are per-run and cumulative across the run's model calls.
- The Manager loop is currently chatty: a small objective took ~13 Manager model calls.
- Most root doctrine and all `prompts/`, `protocols/`, `templates/`, `runbooks/`,
  `evals/`, and `.codex/` material is not loaded by the runtime and is retained as
  human reference.
- The adjudicator, domain-scoping, handoff, and result-packet mechanisms are not
  implemented.

## Decisions

- DEC-001: The Master Blueprint (`docs/walter-bootstrap-master-blueprint.md`)
  supersedes older bootstrap documents and lifecycle terminology.
- DEC-002: Extend the existing runtime; use a separate SQLite operational store,
  retaining conversation sessions.
- DEC-003: Process isolation must fail closed if its backend is unavailable;
  working-directory restrictions alone are insufficient.
- DEC-004 (2026-09-20): Schema-v1 support is dropped. The only operational
  database of value (`.local/walter-operations.db`) is `user_version 2`, so the
  deprecated compatibility fields (`WorkerResult.specialist_request`,
  `ApprovalRequest.reason` alias) are removed. The v1→v2 migration function is
  retained for now; its retirement is a separate later decision.