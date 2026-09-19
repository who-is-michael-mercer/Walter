# Walter on the OpenAI Agents SDK

The Agents SDK is Walter's model boundary, not its source of operational truth. The Manager model receives durable-control tools and an allowlisted policy-reference reader; each specialist is created for one task with tools derived from its capability profile. The deterministic kernel authorizes state transitions, acceptance, approvals, and completion.

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
WALTER_WORKER_MODEL=deepseek/deepseek-v4.1-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Walter explicitly constructs the OpenRouter client and chat-completions models. It does not fall back to the default OpenAI endpoint. Provider trace export and sensitive trace payloads are always disabled. `--trace-sensitive` remains accepted only as a reserved compatibility no-op and cannot enable either. Displayed IDs are labeled `Local trace ID (provider export disabled)`. The reasoning replay hook preserves OpenRouter reasoning content across tool turns.

The default Manager is Kimi K3; workers and independent reviewers default to DeepSeek V4.1 Flash. Each can be overridden independently. The shared client disables automatic HTTP retries and uses a 60-second request timeout; durable specialist execution also has a persisted whole-invocation timeout. Live comparison evidence and its narrow scope are recorded in `docs/IMPLEMENTATION_STATE.md`.

## Durable boundary

Two SQLite databases have distinct roles:

- `.local/walter-sessions.db` stores Agents SDK conversation continuity.
- `.local/walter-operations.db` stores authoritative runs, task graphs, artifacts, decisions, failures, approvals, snapshots, and ordered audit events.

The model must call `inspect_run`, replace the initial sentinel through `set_completion_criteria`, then plan. It proposes work through `plan_tasks`, `delegate_task`, `validate_task`, `review_task`, `accept_task`, `recover_task`, approval-gated `replan_tasks`/`apply_replan`, `request_capability_change`/`apply_capability_change`, generic/current-candidate approval tools, and `finish_run`. Kernel gates remain authoritative.

Manager startup loads only the shared kernel and the entry-point-specific tool guidance. `read_reference` loads a single named policy file on demand. Workers and reviewers receive a bounded JSON context envelope with their task packet, resolved declared inputs and accepted dependency artifacts; revisions add provisional prior results and corrective evidence. Review includes the current candidate and validation evidence. Unrelated run history and authority controls are excluded; stale, unresolved, malformed, or oversized context fails closed.

## Capability profiles

| Profile | Effective runtime access |
| --- | --- |
| `model_only` | Model reasoning and typed result only. |
| `researcher` | SDK hosted `WebSearchTool`; OpenRouter chat-completions compatibility is provider-dependent and not proven by offline tests. |
| `repo_reader` | Read/list/diff tools in an isolated candidate worktree; no writes or command execution. |
| `developer_sandbox` | Read/list/diff, bounded writes, and allowlisted check commands in an isolated candidate worktree. |
| `reviewer` | Read/list/diff access only; acceptance review is commissioned as a fresh reviewer distinct from the author. |

Workers never receive grant-management, approval-decision, acceptance, promotion, or agent-creation tools. Workspace and worker IDs are bound into tool closures. Submissions must match the current assignment ID and worker. Recovered developer revisions receive a fresh workspace through audited `workspace.replaced`; the old workspace is frozen and retained as inspectable partial evidence through assignment history. Eventual cleanup is a separate authorized manual or external operation; automatic retention cleanup is not implemented.

`blocked` and `needs_revision` results are preserved as assignment-bound provisional evidence and routed through trusted failure classification/recovery. They create no artifact and unlock nothing; they are not caught as `TOOL_FAILURE`. A structured capability request includes requested capability, reason, and risk. The Manager persists it and creates an exact approval. `repo_reader` and `developer_sandbox` requests bind a Manager-created workspace into that scope. Rejection cleans the pending workspace. Approved application atomically and idempotently updates durable task capability/workspace and closes the request as `escalated`; redelegation reuses that identity with read-only tools for readers or bounded write/check tools for developers. Developer tasks must declare `compile`, `unittest`, or `pytest` during planning, replanning, and capability change.

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
