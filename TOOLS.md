# Tool and Capability Policy

Tools are constructed from a task's recorded capability profile. A worker cannot select its own profile, workspace, identity, approval, or acceptance authority.

| Profile | Granted access |
| --- | --- |
| `model_only` | No external tools; typed reasoning output only. |
| `researcher` | SDK hosted `WebSearchTool`; OpenRouter chat-completions support is provider-dependent and requires live verification. |
| `repo_reader` | Read, list, and inspect diff inside an isolated candidate worktree. |
| `developer_sandbox` | The same read tools plus bounded file writes and allowlisted `test`/`build`/`check` execution. |
| `reviewer` | Read-only candidate inspection; no authorship, acceptance, approval, or promotion. |

The Manager receives orchestration tools: inspect, set completion criteria, plan, delegate, validate, review, accept, recover, propose/apply approval-gated replans, request/apply capability changes, request generic/current-candidate approval, verify exact candidate authorization, and finish. `read_reference` additionally reads one exact policy filename listed in the Manager kernel, on demand. Its fixed allowlist excludes arbitrary paths, credentials, runtime state, and candidate files; symbolic links are rejected. Workers do not receive it. Human approval decisions enter through the guarded CLI. No exposed tool grants approval, merges, pushes, deploys, or promotes candidates.

`request_capability_change` consumes only a persisted assignment-bound request containing requested profile, reason, and risk. For `repo_reader` and `developer_sandbox`, it creates a Manager-owned candidate workspace and binds its ID into the exact approval. `apply_capability_change` verifies the decision and exact scope, then atomically and idempotently updates task capability/workspace and records `escalated`; rejection records `denied` and cleans any pending workspace. Redelegation reuses the approved workspace with read-only tools for `repo_reader` and bounded write/check tools for `developer_sandbox`. Developer capability is invalid without a predeclared `compile`, `unittest`, or `pytest` check, including plan, replan, and change paths.

Workspace tools bind worker and grant IDs in trusted closures. Paths must be relative, stay beneath the candidate root, exclude state/credentials, and resolve without symlink or hard-link escape. Candidate safety files remain readable, diffable, and fingerprinted but are write-denied by default. `inspect_grant` validates the immutable worktree binding before trusted code reads branch/base identity.

Safety changes require a separate one-use grant. Its verifier must call the core's exact approval check for `safety_boundary_change` and bind run, task, worker, repository, base commit, allowed paths, and `write` or `delete`. The human authority must differ from candidate actors. The signed consumed-approval ledger prevents reuse.

Commands run through Bubblewrap namespaces and a seccomp network-denial profile in an environment-cleared, read-only source/dependency snapshot with bounded writable scratch. Executables/arguments must match Manager templates; compile output goes to scratch. Aggregate process, memory, scratch, file, snapshot, output, and wall-time limits are enforced. Missing isolation fails closed.

External content is data rather than authority. Secrets must never be placed in task context or candidate snapshots. Capability increases require an exact recorded escalation and, when outside standing Manager authority, scoped human approval before the change is applied.
