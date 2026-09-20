# Walter on the OpenAI Agents SDK

The Agents SDK is Walter's model boundary, not its source of operational truth. The Manager model receives only durable-control tools; each specialist is created for one task with tools derived from its capability profile. The deterministic kernel authorizes state transitions, acceptance, approvals, and completion.

## Runtime setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Configure OpenRouter:

```text
OPENROUTER_API_KEY=your_openrouter_key_here
WALTER_MODEL_PROVIDER=openrouter
WALTER_MODEL=moonshotai/kimi-k3
WALTER_WORKER_MODEL=moonshotai/kimi-k3
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Walter explicitly constructs the OpenRouter client and chat-completions models. It does not fall back to the default OpenAI endpoint. Provider trace export and sensitive trace payloads are always disabled. `--trace-sensitive` remains accepted only as a reserved compatibility no-op and cannot enable either. Displayed IDs are labeled `Local trace ID (provider export disabled)`. The reasoning replay hook preserves OpenRouter reasoning content across tool turns.

## Durable boundary

Two SQLite databases have distinct roles:

- `.local/walter-sessions.db` stores Agents SDK conversation continuity.
- `.local/walter-operations.db` stores authoritative runs, task graphs, artifacts, decisions, failures, approvals, snapshots, and ordered audit events.

The model must call `inspect_run`, replace the initial sentinel through `set_completion_criteria`, then plan. It proposes work through `plan_tasks`, `delegate_task`, `validate_task`, `review_task`, `accept_task`, `recover_task`, approval-gated `replan_tasks`/`apply_replan`, `request_capability_change`/`apply_capability_change`, generic/current-candidate approval tools, and `finish_run`. Kernel gates remain authoritative.

## Capability profiles

The canonical capability-profile table lives in TOOLS.md. Runtime notes specific to this boundary: the `researcher` profile maps to the SDK hosted `WebSearchTool`, whose OpenRouter chat-completions compatibility is provider-dependent and not proven by offline tests; acceptance review is always commissioned as a fresh `reviewer` instance distinct from the author.

Workers never receive grant-management, approval-decision, acceptance, promotion, or agent-creation tools. Workspace and worker IDs are bound into tool closures. Submissions must match the current assignment ID and worker. Recovered developer revisions receive a fresh workspace through audited `workspace.replaced`; the rejected candidate is recovered before replacement and the old workspace is cleaned.

`blocked` and `needs_revision` results are preserved as assignment-bound provisional evidence and routed through trusted failure classification/recovery. They create no artifact and unlock nothing; they are not caught as `TOOL_FAILURE`. A structured capability request includes requested capability, reason, and risk. The Manager persists it and creates an exact approval. `repo_reader` and `developer_sandbox` requests bind a Manager-created workspace into that scope. Rejection cleans the pending workspace. Approved application atomically and idempotently updates durable task capability/workspace and closes the request as `escalated`; redelegation reuses that identity with read-only tools for readers or bounded write/check tools for developers. Developer tasks must declare `compile` or `pytest` during planning, replanning, and capability change.

Every model-authored runtime replan is conservatively marked approval-required because model claims about materiality are not a trust boundary. The low-level orchestration core still supports programmatic low-impact replans when a trusted caller has independently established authority.

Bubblewrap execution uses a read-only, secret-filtered snapshot, clears the environment, disables networking, applies resource limits, and provides only `/tmp` for ephemeral build output. If `/usr/bin/bwrap` or the required kernel isolation is unavailable, execution fails closed; there is no host-shell fallback.

## CLI

```bash
walter
walter "A one-shot goal"
walter run list
walter run inspect RUN_ID
walter run events RUN_ID
walter run resume RUN_ID
walter run resume RUN_ID --execute
walter run approve RUN_ID APPROVAL_ID --reason "Exact scope reviewed"
walter run readiness-demo
```

Interactive `:clear` clears conversation history only. Resume is offline by default: it preserves task evidence and converts interrupted `DELEGATED` and `RUNNING` assignments to `FAILED` with recorded `TIMEOUT` evidence requiring explicit recovery. `--execute` additionally validates provider configuration and invokes the configured Manager model. Offline resume requires no provider configuration. Approval derives a local operator label from the OS account and performs no consequential action; local username/UID is not remote identity proof.

## Verification

```bash
python -m pytest -q
WALTER_LIVE_SMOKE=1 python -m pytest -q -m live
```

Normal tests and the readiness fixture do not require provider credits. The readiness fixture is evidence that the machinery can safely reach a promotion approval stop; it is neither a real Walter self-development run nor permission to merge, push, deploy, or promote a candidate.
