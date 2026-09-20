# Permissions and Escalation

## Authority chain

Workers act only inside their task packet and granted capability. Trusted executors produce programmatic evidence. Independent reviewers evaluate but cannot author, accept, or promote. The Manager owns task acceptance and run completion. The human owns extraordinary authority and consequential promotion.

For a material candidate, the required chain is:

`worker submission → trusted validation → independent review → Manager acceptance → exact human approval → separate promotion mechanism`.

No participant may collapse two authorities into one claim. Human approval records permission for a proposed action; it does not itself perform the action.

## Standing Manager authority

The Manager may autonomously make reversible orchestration choices within the accepted objective: decompose and sequence work, assign profiles already allowed by policy, create/replace/retire workers, request corrections, commission review, classify failures, and accept artifacts that pass declared gates. Trusted programmatic callers may apply bounded low-impact replans through the core; every model-facing runtime replan is conservatively human approval-gated.

## Human approval required

Request approval for:

- merge to a protected/stable branch, external push, release, or deployment;
- destructive deletion or irreversible action;
- spending, subscriptions, or binding commitments;
- external communication or representation for the human;
- secrets, credentials, privileged access, or sensitive data changes;
- permission, sandbox, safety-boundary, or control-plane changes;
- material objective/scope change or extraordinary replan;
- capability escalation outside standing Manager authority.

## Exact scope

An approval request records category, action, canonical scope/digest, target, rationale, risk, artifact references, optional requested capability, and lifecycle status. The human decision is immutable and auditable. Approval is valid only when action and scope match exactly. A different artifact/commit, branch/base, target, diff, permission, deployment, or destructive consequence requires a replacement request.

Supersession preserves both requests and links them. An approval bound to active `DELEGATED`/`RUNNING`/`SUBMITTED`/`REVIEWING` work cannot be superseded until the Manager records failure and recovery. Replaced gates return non-running tasks to a blocked state until the replacement is approved.

Rejected requests remain rejected; decisions cannot be overwritten. Required pending approvals prevent run completion. Candidate actions use trusted recomputation of the current accepted artifact, content/workspace identity, candidate branch/base, diff digest, and target before exact authorization. Walter has no merge, push, deploy, or promotion tool.

The local CLI derives `local-os:<username>:uid:<uid>` from the current OS session and does not accept a caller-supplied identity. This is useful audit attribution on a trusted single-user host, not cryptographic authentication or proof of a remote person's identity.

Ordinary developer grants cannot mutate Walter safety paths. A safety-boundary grant requires a core-backed verifier for an exact approved scope, distinct human authority, exact allowed paths/operation, and one-time consumption. Default denial remains in force even though these files are readable and fingerprinted.

A worker capability request is a proposal, never self-granted authority. It must bind to the active assignment and include requested profile, reason, and risk. The Manager may deny it or request human approval for the exact task/profile/workspace scope. Repository-read and developer scopes contain the ID of an exact Manager-created workspace. `approved` is intermediate; authority changes only when atomic, idempotent application succeeds and the request becomes `escalated`. Pending workspaces are cleaned on denial/failure and reused only after exact approval, read-only for `repo_reader` and through bounded write/check tools for `developer_sandbox`. Developer authority additionally requires a declared `compile` or `pytest` check on every plan, replan, and change path.

## Worker prohibitions

Workers cannot create agents, broaden goals, change capability or policy, access ungranted tools/context, accept their output, grant approval, promote code, or make external commitments. Capability unavailability is a recorded blocker or failure, never permission to bypass enforcement.

Self-build readiness demonstrates these gates with a harmless fixture. It grants no authority to begin real Walter self-development or promote a candidate.
