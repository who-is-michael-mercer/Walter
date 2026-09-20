# Walter Audit Remediation — Final State

Rebuilt 2026-09-20; closed 2026-09-20. Supersedes the 2026-09-19 remediation
plan. **All tasks T001–T048 are complete.** Verified-complete work is
summarized in **Work Completed**; follow-up findings from the first real run
live in `docs/first-real-run-gap-report.md`.

## Status headline

- Offline suite: **160 passed, 1 skipped (opt-in live), 0 failed**; live smoke passes.
- `main` == `origin/main`; working tree clean; stash empty; only `main` locally.
- Agents SDK pinned: `openai-agents>=0.22.3,<0.23` (installed 0.22.3).
- Final validation gate (bottom of this document): **all 9 items pass**.
- Audit Phases A–J (T001–T048): **complete**.

## Work completed (verified)

| Milestone | Tasks | Evidence |
| --- | --- | --- |
| M1 — Green, protected baseline | T001–T005 | Suite green; usage wiring + AGENTS.md rewrite committed and pushed |
| M2 — Residue-free repository | T006–T015 | Session export, Crush residue, stale pycache, vestigial `runtime/` removed; `.gitignore` updated; merged candidate/feature branches deleted locally and remotely; stashes dropped; wip branch removed locally |
| M3 — Doctrine wired into runtime | T016–T021 | `load_system_prompt()` in `adapter.py`; `DurableController.instructions()` = SYSTEM_PROMPT.md + trimmed operational appendix + run ID; composition pinned by test; AGENTS.md updated |
| M4 — Legacy path eliminated | T022–T025 | `WORKER_INSTRUCTIONS`, `RUNTIME_APPENDIX`, `_walter_instructions`, legacy `delegate_task` and the no-controller `build_walter` path deleted; durable-path behavior test in place |
| M5 — Usage accounting consolidated | T026–T029 | Decision: **wire**. `UsageBudget` enforced pre-call in `UsageRecordingModel`; budget gate tested; normalization single-sourced in `usage.py` |
| M6 — Supply-chain guard | T030 | SDK pinned (`a3468bd`); suite green |
| M7 — Behavioral proof offline | T031, T032, T034, T035 | `tests/fakes.py` scripted SDK model; `tests/test_e2e.py` drives criteria→plan→delegate→validate→review→accept→`finish_run` offline with event-chain and usage assertions; interruption→FAILED(TIMEOUT)→recover test; CLI approval negative-path tests |
| M8 — Documentation reconciled | T036–T042 | Python-only sandbox limitation in TOOLS.md; task-state list and capability table single-sourced; README trimmed to install/usage/map; IMPLEMENTATION_STATE.md counts current; docs-vs-code pass done |
| M9 — Live validation | T043, T044 | Live smoke passes; researcher verdict recorded (hosted `WebSearchTool` rejected by OpenRouter chat completions — profile currently unusable; README/TOOLS.md/AGENTS_SDK.md updated); first real external-repo run executed with DeepSeek/Qwen workers — blocked honestly, findings in `docs/first-real-run-gap-report.md` |
| M10 — Hardening & lifecycle | T045–T048 | Provider-failure injection test (`tests/test_e2e.py`); DEC-004 recorded (schema-v1 dropped, DB is `user_version 2`); `WorkerResult.specialist_request` and `ApprovalRequest.reason` alias removed; eval runner wired — EVAL-001/002/003 pass 3/3 offline |

### Operator-completed work beyond the original plan

- Thread-safe durable store across SDK tool-dispatch threads (`6cfa55a`).
- Env-configured per-run usage budgets + clean CLI budget-exhaustion reporting
  (`214a049`, `c78f8f1`).
- Forward-compatible snapshot loading (`7533baf`); stale workspace-grant
  reconciliation (`d694638`).
- Developer validation scoped to candidate test files (`c61fa51`, `9554e3b`).
- One live model-driven end-to-end run completed 2026-09-20 (run
  `1b6affd4233446de9093d6c4a92b8c6c`; 16 calls, ~299k tokens, ~$0.38, within
  budget) — recorded in `docs/IMPLEMENTATION_STATE.md`.

### Deviations from the original plan (honest record)

- T012–T014 (stash/wip evidence reports) were superseded by **preservation**:
  the wip branch and stash content were pushed to origin
  (`codex/overnight-manager-v1`, `preserve/overnight-manager-v1-stash`) before
  local deletion, eliminating loss risk without a per-hunk audit.
- T045 item 2 (approval supersession under active work) was already covered by
  `test_active_task_approval_cannot_be_superseded_until_failure_recovery`;
  only the provider-failure half needed a new test.
- T044's run did not reach `completed`; it failed with a precisely documented
  gate (attempts exhausted after three honest worker failures), which the task
  accepts. The gap report is the deliverable.

## What remains (post-remediation follow-ups, not audit tasks)

From `docs/first-real-run-gap-report.md` — candidates for new operator-reviewed
tasks, none started:

1. `required_inputs` soft-lock: CLI/adapter never registers target-repo inputs;
   stuck `PLANNED` tasks cannot be classified; replan is the only route.
2. Opaque delegation-gate error conflates inputs/readiness/attempts.
3. `replan_tasks` add-path drops capability and predeclared checks.
4. Weak non-default workers (DeepSeek/Qwen flash tiers) and worker `max_turns`.
5. Manager-loop chattiness (~13–28 calls per small objective).
6. Placeholder `.env` key passes validation and orphans a run on 401.

Standing limitations (documented, not blockers): OpenRouter-only provider;
`researcher` profile unusable with that provider; Python-only sandbox
templates; adjudicator / domain-scoping / handoff / result-packet mechanisms
unimplemented.

## Non-actionable audit findings (register; no task)

| Finding | Why no task |
| --- | --- |
| Kernel/store/sandbox quality praise | Informational |
| Keep readiness fixture, `--trace-sensitive` no-op, superseded bootstrap docs | Audit says keep |
| `orchestration.py` god-module watch | "Not yet worth splitting"; the file to watch |
| `adapter._invoke` per-call config rebuild | Noted; no audit recommendation |
| AST compile-snippet duplication | Noted; cleanup plan did not act |
| Lint/format/typecheck tooling | Deferred; operator's call |
| Multi-language sandbox templates | Deferred pending demonstrated requirement (limitation documented in TOOLS.md) |
| Second provider | Deferred |
| Python 3.14 floor vs `>=3.11` | Informational; no CI to act on |
| `.env` real key | Correctly gitignored; hygiene only (note: repo `.env` currently holds the placeholder; the real key lives in the operator's shell environment) |
| `.codex/` dev scaffolding | Dev-time only; runtime is Codex-independent |
| `templates/`, `prompts/`, `protocols/`, `runbooks/` unused by runtime | Kept as human material; no runtime cost |
| Phase 7 capability expansion | Explicitly deferred; each addition requires demonstrated need |
| v1→v2 migration function | Retained per DEC-004; retirement is a separate later decision |

## Final validation gate — status: ALL PASS (2026-09-20)

1. Offline suite: 160 passed, 1 skipped (live), 0 failed. ✓
2. `git status --porcelain` clean; `git stash list` empty; local branches: only
   `main`. ✓
3. No `WORKER_INSTRUCTIONS` / `RUNTIME_APPENDIX` / `_walter_instructions` /
   legacy `def delegate_task` in `src/`. ✓
4. Exactly one normalization home (`usage.py`), consistent with the "wire"
   decision. ✓
5. Durable-instructions composition test passes; instructions contain
   SYSTEM_PROMPT.md content. ✓
6. `pip show openai-agents` = 0.22.3, within `>=0.22.3,<0.23`. ✓
7. Offline E2E (`tests/test_e2e.py`) completes through `finish_run`;
   interruption test green. ✓
8. Docs spot-check: AGENTS.md, AGENTS_SDK.md, README.md, TOOLS.md,
   IMPLEMENTATION_STATE.md accurate against code. ✓
9. `walter run readiness-demo` executes the offline fixture against real
   Bubblewrap. ✓

## Audit coverage matrix

Every audit finding is either remediated (Work Completed), resolved as a
deferred task (M9/M10 rows), captured as a follow-up (What remains), or
non-actionable (register above). No open audit tasks remain.

