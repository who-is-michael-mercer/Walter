# T044 — First real external-repository run: gap report

Date: 2026-09-20. Run `04976c30a16c4b82aefa5a9da1894d59` (scratch repo outside
the Walter checkout: one `calc.py`, one `test_calc.py`). Manager:
`moonshotai/kimi-k3`. Workers: `deepseek/deepseek-v4-flash` (attempts 1–2),
`qwen/qwen3.7-flash` (attempt 3). Objective: add `multiply(a, b)` with tests.

## Outcome

Run did **not** complete; it is active and precisely gated: task `dev-multiply`
is `FAILED` with attempts exhausted (3/3), so only the REPLAN recovery route
remains. Stopped there to bound credits (42 model calls, ~625k tokens total,
capped by `WALTER_MAX_TOTAL_TOKENS`; the budget gate fired cleanly and honestly).

The objective was achieved in evidence terms: the durable kernel, approval and
replan gates, recovery taxonomy, usage accounting, and budget enforcement all
worked against real models across three resume cycles, and every failure was
honest. No evidence was manufactured at any point.

## Timeline

1. Manager planned one `developer_sandbox` task with predeclared `pytest`
   check — and declared `required_inputs: [calc.py, test_calc.py]`.
2. Delegation was kernel-gated 4× (`Worker, readiness or attempt gate failed`)
   because nothing had registered those inputs; the Manager diagnosed this
   correctly from durable state, proposed a replan, and **recommended the
   operator deny it** (the replacement task would have lost its
   `developer_sandbox` capability and `pytest` check — see gap 3).
3. Operator denied the replan and registered the inputs via the kernel
   (`input.registered` events). Delegation gate cleared.
4. Attempt 1 (DeepSeek): worker returned an intent statement, no work →
   `BAD_OUTPUT` → REVISE.
5. Attempt 2 (DeepSeek): empty workspace diff; trusted pytest validation
   failed ("No candidate test files were added or changed") →
   `REPEATED_BAD_OUTPUT` → REPLACE. Bad artifact rejected, provenance kept.
6. Operator approved the Manager's reopen replan (capability/checks preserved).
7. Attempt 3 (Qwen): worker burned its 12-turn budget without returning a
   structured `WorkerResult` → `MaxTurnsExceeded` → `TOOL_FAILURE`. Attempts
   exhausted; task `FAILED`.

## Gaps found (candidates for new tasks; nothing fixed in situ)

1. **`required_inputs` soft-lock (highest priority).** Declaring repo files as
   `required_inputs` makes a task undelegatable unless inputs are registered,
   but the CLI exposes no way to register them (only a kernel call), and the
   planning tool gives no warning. Worse, the stuck task cannot be classified
   (`PLANNED → FAILED` is illegal), so `recover_task` is unavailable and replan
   is the only route. Consider: adapter/CLI auto-registers target-repo files at
   run start, or `plan_tasks` rejects unregistered input declarations, or the
   kernel allows failing a `PLANNED` task whose inputs can never resolve.
   **Resolved 2026-09-20:** new `register_repository_inputs` Manager tool
   (trusted code reads each repo file and registers a `sha256:` digest with the
   kernel) plus plan-time validation that rejects unresolvable
   `required_inputs` with a precise, actionable error. The soft-lock can no
   longer arise through the tool surface; covered by adapter tests.
2. **Opaque delegation-gate error.** `Worker, readiness or attempt gate failed`
   conflates inputs, readiness, workspace, approval, and attempt-budget gates.
   The Manager spent ~13 calls diagnosing what one precise error (`missing
   registered inputs: calc.py, test_calc.py`) would have settled immediately.
   **Resolved 2026-09-20:** the kernel now names the precise blocker —
   `Task is not ready: Required input is unavailable: <name>`,
   `Input task is not accepted: <name> (<status>)`,
   `Attempt budget exhausted (n/max)`, or `Worker identity is not delegatable` —
   via a shared `_readiness_blocker` used by the delegate gate. Pinned by
   `test_delegate_gate_names_the_precise_blocker`.
3. **`replan_tasks` add-path drops capability and checks.** `propose_replan`
   builds `TaskNode(packet=...)` with defaults (`model_only`, no checks), so a
   replacement developer task silently loses `developer_sandbox` and `pytest`.
   The Manager detected this and recommended denying its own proposal — good
   behavior working around a real tool defect.
   **Resolved 2026-09-20:** `replan_tasks`/`propose_replan` accept
   `add_capabilities`/`add_checks` (same validation as `plan_tasks`, via a
   shared `_task_nodes` builder), so added tasks keep their declared capability
   and predeclared checks. Pinned by adapter tests.
4. **Weak non-default workers.** Neither DeepSeek v4-flash nor Qwen3.7-flash
   drove the workspace tools to a real diff (two empty submissions, one
   12-turn exhaustion). Worker `max_turns=12` may also be tight for
   multi-step file work. Non-Kimi worker selection needs either stronger
   models or worker-loop tuning.
   **Resolved 2026-09-20 (tooling half):** worker/reviewer turn budget is now
   configurable via `WALTER_WORKER_MAX_TURNS` (default raised 12 → 24). The
   model-quality half is a selection concern, not code: flash-tier workers are
   not dependable for multi-step file work.
5. **Manager chattiness.** 28 Manager calls / ~625k tokens for a one-function
   objective (partly forced by gap 2). Prompt/tool-result economy is worth a
   look once the gate errors are precise.
   **Resolved 2026-09-20:** mutating Manager tools now return a compact durable
   receipt (task statuses, attempts, artifacts, pending approvals, failures,
   usage totals) instead of the full run snapshot; `inspect_run` remains the
   full-truth read. This removes the per-call full-JSON echo that dominated
   token spend.
6. **Placeholder `.env` hazard (minor).** A `.env` containing the example
   placeholder key passes config validation (non-empty) and produces a 401 on
   the first call, leaving an active orphan run (`4cd153c6…` in the scratch
   DB). Consider validating the key shape or failing fast on 401.
   **Resolved 2026-09-20:** `RuntimeConfig.from_env` rejects the
   `.env.example` placeholder value before any run is created.

## What worked (positive evidence)

- Durable resume across three `--execute` cycles with zero state corruption.
- Typed approvals: replan deny/approve flowed through the CLI with local
  operator identity recorded; the kernel enforced exact scope.
- Recovery taxonomy: REVISE → REPLACE → reopen-replan all behaved as designed.
- Trusted validation: pytest scoping caught the empty-diff candidate.
- Usage accounting: all 42 calls recorded with model/role identity, including
  failures; the total-token budget stopped the run cleanly at the cap.
- Manager doctrine: honest status, no manufactured evidence, correct
  escalation when autonomous routes were exhausted.
