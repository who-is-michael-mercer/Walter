# Walter Bootstrap Master Blueprint

> **Status:** Canonical bootstrap architecture and implementation specification  
> **Purpose:** Define the complete path from Walter's current delegated-task runtime to a safe, inspectable, self-build-ready orchestration system.  
> **Source documents:** This blueprint consolidates and supersedes the bootstrap guidance in `walter-bootstrap-design.md` and `walter-bootstrap-engineering-spec.md` while preserving their compatible design intent. The original documents remain useful historical references.  
> **Stop condition:** This blueprint ends at **self-build readiness**. It does not authorize Walter's first autonomous self-development feature or any promotion of candidate Walter code into stable `main`.

---

## 0. Executive Summary

Walter is not intended to become a permanent collection of named agents. Walter is intended to become an **organization generator**: a Manager-controlled system that can turn a human objective into a bounded plan, create only the temporary specialists required, enforce dependencies and permissions, inspect candidate outputs, promote only accepted artifacts into canonical state, recover from failures deliberately, and request human approval before consequential actions.

The central architectural idea is simple:

> **Walter's power should come from managing work correctly, not from possessing unrestricted self-authority.**

The bootstrap therefore does **not** aim to make Walter maximally autonomous as quickly as possible. It aims to construct a trustworthy control plane around autonomy.

The bootstrap is successful when Walter can safely do all of the following:

- accept a human objective and create a durable run;
- define measurable completion criteria;
- decompose the objective into narrow specialist tasks;
- build and enforce a dependency graph;
- create temporary workers with least-privilege capabilities;
- distinguish worker completion from Manager acceptance;
- persist plans, events, decisions, artifacts, approvals, and failures independently of conversation history;
- classify failures before recovery;
- revise or replan explicitly rather than silently;
- execute development work only inside isolated, bounded worktrees;
- perform programmatic validation and independent review;
- stop at a scoped human approval gate before promotion of self-modifying work.

The intended progression is:

```text
Current Walter
    ↓
Human-directed bootstrap Walter
    ↓
Self-build-ready Walter
    ↓
First Walter-built candidate
    ↓
Independent validation + human promotion decision
```

This document specifies the middle transition.

---

# Part I — Design Doctrine

## 1. Design Goal

Walter should operate as a Manager-led organization of temporary specialists.

For each objective, Walter should:

1. determine the minimum viable work required;
2. define completion criteria before execution;
3. decompose the objective into bounded specialist lanes;
4. identify dependencies before scheduling work;
5. create only the workers actually needed;
6. grant each worker only the tools and context required for its lane;
7. require inspectable deliverables;
8. evaluate outputs before accepting them as project truth;
9. preserve a durable record of decisions, artifacts, revisions, failures, and approvals;
10. replan only through explicit, logged changes;
11. request human approval before high-impact actions;
12. evolve itself only through isolated, reviewable candidate changes.

Walter is therefore not merely a prompt wrapper and not merely an agent swarm. It is a **bounded work-organization system with an explicit control plane**.

---

## 2. Core Principles

### 2.1 The Manager Owns Reality

The Walter Manager is the authoritative controller for a run. It owns:

- objective interpretation;
- completion criteria;
- task decomposition;
- dependency graph construction;
- worker assignment;
- acceptance decisions;
- failure classification;
- recovery decisions;
- replanning;
- run completion;
- escalation boundaries;
- canonical project state promotion.

The Manager is not a thin router between agents. It is the orchestration authority.

### 2.2 Workers Are Temporary and Bounded

Workers are short-lived specialists. Each worker should have:

- one lane;
- one objective;
- one primary inspectable deliverable;
- explicit inputs;
- explicit constraints;
- explicit acceptance criteria;
- explicit capability grants;
- a stop condition;
- a finite lifecycle.

Workers may exercise high autonomy **inside** their assigned lane, but they may not:

- broaden scope;
- redefine the parent objective;
- create or manage other agents;
- grant themselves additional tools;
- alter approval or safety policy;
- decide that their own output is accepted;
- make external commitments on the human's behalf.

### 2.3 Completion Is Not Acceptance

This is a non-negotiable architectural invariant.

A worker can complete its work and submit a candidate artifact without that artifact becoming project truth.

```text
Worker completion = candidate output exists
Manager acceptance = candidate output has passed the required gates
```

Only accepted outputs may:

- satisfy dependencies;
- unlock downstream tasks;
- enter canonical project state;
- contribute to run completion.

Worker confidence, self-checks, or statements of success are evidence only.

### 2.4 Safety Is Stronger Than Cleverness

Walter should prefer:

- explicit state over implicit conversational assumptions;
- isolated workspaces over live mutation;
- typed artifacts over free-form handoffs;
- observable decisions over hidden reasoning side effects;
- staged promotion over direct modification;
- independent validation over self-trust;
- least privilege over broad convenience;
- human approval over autonomous authority when consequences are material.

A clever system that cannot explain or reconstruct what it did is not ready for self-development.

### 2.5 Tool Access Follows Least Privilege

Capability is granted per task, not per identity.

A worker should receive only the tools required for the lane it owns. Capability requests outside that profile must flow through an explicit escalation mechanism.

### 2.6 Deterministic Invariants Belong in Code

The model may reason about planning, judgment, acceptance, recovery, and tradeoffs. It must not be trusted to enforce deterministic system invariants through prompt obedience alone.

The following belong in executable orchestration code:

- legal state transitions;
- dependency readiness;
- retry and revision limits;
- capability grants;
- workspace boundaries;
- approval gates;
- artifact promotion rules;
- persistence;
- run completion rules.

Walter should reason **inside** a control system. Walter should not *be* the control system.

---

# Part II — System Architecture

## 3. Architectural Layers

Walter's target architecture consists of six primary layers plus a cross-cutting observability plane.

### 3.1 Human Authority Layer

The human provides:

- objectives;
- material scope changes;
- approval decisions;
- exceptions;
- final authority over high-impact promotion actions.

The human should not be interrupted for routine orchestration decisions Walter can safely make itself.

### 3.2 Walter Manager Layer

The Manager owns:

- planning;
- decomposition;
- delegation;
- review orchestration;
- acceptance;
- recovery;
- replanning;
- completion checks;
- escalation.

### 3.3 Orchestration Core

The orchestration core owns machine-enforced execution semantics:

- `Run` state;
- `WorkPlan` state;
- task graph;
- task lifecycle transitions;
- dependency readiness;
- worker assignments;
- retry/revision limits;
- approval gating;
- canonical artifact promotion.

This layer must be explicit, serializable, testable, and inspectable independently of model behavior.

### 3.4 Worker Runtime

The worker runtime creates temporary specialists from typed task definitions.

It is not a permanent multi-agent hierarchy. Workers exist only for the duration necessary to complete or fail a bounded lane.

### 3.5 Artifact System

Artifacts move through a controlled lifecycle:

```text
Candidate → Validated/Reviewed → Accepted → Canonical
```

Artifacts must carry enough metadata to explain:

- who or what produced them;
- for which task and run;
- which inputs they depended on;
- which version they represent;
- which checks were performed;
- who reviewed them;
- whether they were accepted, rejected, superseded, or remain provisional.

### 3.6 Project State

Project state preserves durable information across runs and sessions:

- accepted artifacts;
- canonical decisions;
- constraints;
- unresolved issues;
- run history;
- approvals;
- project-level references;
- lineage between artifacts and decisions.

### 3.7 Observability and Audit Plane

Structured events span every layer.

Events provide the substrate for:

- auditability;
- debugging;
- recovery after interruption;
- future GUI/control-panel views;
- regression analysis;
- run timelines;
- operator confidence.

This plane must exist **before** Walter begins self-development.

---

## 4. Conversational Memory vs. Operational State

Walter's Agents SDK session history and Walter's operational state are different systems with different responsibilities.

### Conversational memory may contain:

- dialogue history;
- previous user statements;
- conversational context;
- model-facing continuity.

### Operational state must contain:

- objective;
- completion criteria;
- plan;
- tasks;
- dependencies;
- task states;
- worker assignments;
- artifacts;
- acceptance decisions;
- failures;
- replans;
- approvals;
- events;
- run status.

**Operational truth must never depend on reconstructing execution from chat text.**

A restart of Walter should not force the system to infer which task was accepted, which approval was granted, or what branch contains candidate work by rereading conversational history.

The current `SQLiteSession` mechanism may remain useful for conversation persistence, but it is not sufficient as the sole orchestration state store.

---

# Part III — Canonical Data Model

## 5. Core Types

The implementation should include or adapt the following types:

- `Run`
- `WorkPlan`
- `TaskNode`
- `WorkerAssignment`
- `WorkerResult`
- `Artifact`
- `ArtifactValidation`
- `AcceptanceDecision`
- `Decision`
- `Event`
- `WorkerFailure`
- `RecoveryDecision`
- `ReplanProposal`
- `ApprovalRequest`
- `ApprovalDecision`
- `CapabilityProfile`
- `WorkspaceGrant`

Exact module structure is an engineering choice. Semantic separation is not.

---

## 6. Run Model

Every user objective should create or attach to a durable run.

Conceptually:

```python
class Run(BaseModel):
    id: str
    objective: str
    constraints: list[str]
    status: RunStatus
    plan: WorkPlan
    tasks: dict[str, TaskNode]
    accepted_artifacts: list[str]
    decisions: list[str]
    approvals: list[str]
    unresolved_issues: list[str]
    event_cursor: int | None
    final_result: str | None
    created_at: datetime
    updated_at: datetime
```

The durable run is the Manager's machine-readable execution record.

### Required properties

A run must be:

- serializable;
- reloadable;
- versionable or migratable;
- inspectable without invoking a model;
- linked to its events and artifacts;
- protected from impossible state transitions.

---

## 7. WorkPlan

A `WorkPlan` expresses Walter's current executable interpretation of the objective.

Required fields should include:

- objective;
- completion criteria;
- task IDs;
- assumptions;
- risks;
- status;
- revision count;
- revision history;
- current revision identifier;
- timestamps.

A plan may evolve, but changes must be explicit.

The Manager should never silently mutate the plan in memory and continue as if nothing changed.

---

## 8. TaskNode

A `TaskNode` represents one specialist lane.

Required fields should include:

- stable task ID;
- role/lane;
- objective;
- deliverable;
- context;
- required inputs;
- constraints;
- acceptance criteria;
- dependency IDs;
- capability profile;
- workspace grant if applicable;
- current status;
- attempts;
- revision count;
- maximum attempts/revisions;
- worker assignment;
- result/artifact references;
- blocker/failure state;
- timestamps.

The current `TaskPacket` contract should be evolved where sensible rather than discarded without reason.

---

## 9. Artifact Model

An artifact is a structured project output, not merely a filename or model string.

Required metadata should include:

- artifact ID;
- run ID;
- producer task ID;
- producer worker ID;
- artifact type;
- location or content reference;
- version;
- predecessor/superseded artifact if any;
- source/input artifact references;
- validation state;
- review state;
- acceptance state;
- reviewer references;
- timestamps.

The artifact system must support lineage.

For example:

```text
ART-014 v1 candidate
    ↓ revision requested
ART-014 v2 candidate
    ↓ automated tests passed
    ↓ independent review passed
    ↓ manager accepted
ART-014 v2 canonical
```

---

## 10. Decision Model

Material orchestration choices should create structured decisions.

A decision should capture:

- context;
- options considered where relevant;
- selected action;
- reason;
- evidence;
- consequences;
- affected entities;
- timestamps.

Examples include:

- replacing a worker;
- reopening an upstream task;
- accepting an artifact despite a non-blocking warning;
- selecting a replan option;
- abandoning an optional enhancement.

---

# Part IV — Canonical Task Lifecycle

## 11. One State Vocabulary

Walter must have one canonical executable task state machine.

The richer bootstrap lifecycle should replace or explicitly map older documentation that uses simplified states such as `ACTIVE`, `REVIEW`, `REVISION`, and `COMPLETE`.

Recommended canonical states:

- `PLANNED`
- `READY`
- `DELEGATED`
- `RUNNING`
- `SUBMITTED`
- `REVIEWING`
- `REVISION_REQUIRED`
- `ACCEPTED`
- `REPLACED`
- `BLOCKED`
- `FAILED`
- optionally `CANCELLED` when human or plan changes invalidate the task.

### Semantic mappings from older doctrine

```text
ACTIVE   ≈ DELEGATED/RUNNING
REVIEW   ≈ SUBMITTED/REVIEWING
REVISION ≈ REVISION_REQUIRED
COMPLETE ≈ ACCEPTED
```

`ACCEPTED` is preferred over `COMPLETE` because it reinforces the completion-vs-acceptance boundary.

---

## 12. State Transition Rules

Allowed transitions must be centralized and enforced by code.

Illustrative valid paths:

```text
PLANNED → READY
READY → DELEGATED
DELEGATED → RUNNING
RUNNING → SUBMITTED
SUBMITTED → REVIEWING
REVIEWING → ACCEPTED
REVIEWING → REVISION_REQUIRED
REVISION_REQUIRED → DELEGATED
REVIEWING → REPLACED
RUNNING → BLOCKED
RUNNING → FAILED
```

Transitions should carry a reason and emit an event.

Invalid transitions must raise an error.

Examples:

- `ACCEPTED → RUNNING` is illegal;
- `PLANNED → RUNNING` is illegal without readiness and delegation;
- `READY → ACCEPTED` is illegal without submission and review;
- a blocked task may not silently resume without the blocking condition being resolved.

---

## 13. Readiness and Dependency Semantics

A task becomes `READY` only when:

- all required upstream tasks or artifacts are accepted;
- required inputs exist;
- required access/capabilities are available;
- acceptance criteria are defined;
- no unresolved approval or gate blocks execution.

A downstream task may not execute merely because an upstream worker said it finished.

Only accepted upstream state satisfies dependencies.

If an upstream task fails, is rejected, or is reopened, affected downstream tasks must remain or become blocked until graph consistency is restored.

---

# Part V — Planning, Delegation, and Acceptance

## 14. Work Planning

Walter converts a human objective into:

```text
Outcome → Workstreams → Tasks → Dependencies → Acceptance Criteria → Execution Order
```

Planning rules:

1. Decompose by deliverable, not vague activity.
2. Stop decomposing when a task fits one specialist lane.
3. Define acceptance criteria before delegation.
4. Identify dependencies before spawning workers.
5. Use progressive elaboration rather than over-specifying downstream tasks whose inputs do not yet exist.
6. Distinguish required discovered work from optional enhancement work.
7. Use domain-scoping specialists when Walter lacks enough knowledge to decompose responsibly.
8. Preserve explicit assumptions and risks.

---

## 15. Worker Delegation

Every worker receives a structured, minimum-sufficient assignment.

A task packet should include:

- task ID;
- role;
- objective;
- deliverable;
- minimum necessary context;
- required inputs;
- constraints;
- dependency references;
- acceptance criteria;
- capability profile;
- workspace grant if applicable;
- stop condition.

Workers should not receive entire project history by default.

Accepted upstream information should be preferred over raw upstream worker chatter.

---

## 16. Acceptance Flow

Required flow:

```text
worker executes
    ↓
worker submits candidate artifact/result
    ↓
programmatic checks where applicable
    ↓
review if judgment remains or risk requires it
    ↓
Manager acceptance decision
    ↓
accepted artifact enters canonical state
    ↓
dependents may unlock
```

The Manager may decide:

- `ACCEPT`;
- `REVISE`;
- `REJECT`;
- `REPLACE`;
- `REPLAN`;
- `ESCALATE` when human authority is required.

Acceptance must be explicit and recorded.

---

# Part VI — Durable Events, Artifacts, and Operational Persistence

## 17. Persistence Is a Precondition for Self-Building

A major bootstrap correction is required here:

> **Walter must already possess minimum viable durable event, artifact, decision, approval, and run-state persistence before Walter is asked to build Walter.**

These systems must not be deferred as Walter's first self-development feature.

Otherwise Walter would be modifying the system that is supposed to record and govern the modification before that governing layer is trustworthy.

---

## 18. Event Architecture

Every significant orchestration mutation should emit a structured event.

Recommended event families include:

### Run events

- `run.created`
- `run.started`
- `run.paused`
- `run.resumed`
- `run.completed`
- `run.failed`

### Plan events

- `plan.created`
- `plan.revised`
- `plan.replan_proposed`
- `plan.replan_applied`

### Task events

- `task.created`
- `task.ready`
- `task.delegated`
- `task.started`
- `task.submitted`
- `task.review_started`
- `task.revision_required`
- `task.accepted`
- `task.blocked`
- `task.failed`
- `task.replaced`

### Artifact events

- `artifact.created`
- `artifact.submitted`
- `artifact.validation_started`
- `artifact.validation_completed`
- `artifact.reviewed`
- `artifact.accepted`
- `artifact.rejected`
- `artifact.superseded`

### Failure/recovery events

- `failure.classified`
- `recovery.decided`
- `retry.scheduled`
- `worker.replaced`

### Capability/approval events

- `capability.requested`
- `capability.denied`
- `capability.escalated`
- `approval.required`
- `approval.granted`
- `approval.rejected`
- `approval.expired` if implemented

### Workspace events

- `workspace.created`
- `workspace.boundary_violation`
- `workspace.cleaned`

Events should be append-oriented and sufficient to reconstruct a meaningful run timeline.

The bootstrap does not require an enterprise event-streaming platform. It requires a small, reliable, durable event store.

---

## 19. Operational Persistence Requirements

The persistence layer must store enough information to recover after interruption without relying on chat replay.

At minimum persist:

- runs;
- plans and revisions;
- tasks;
- task states;
- worker assignments;
- artifacts and lineage;
- acceptance decisions;
- failures;
- recovery decisions;
- replans;
- approvals;
- structured events;
- unresolved issues;
- final run state.

The exact storage technology is an implementation decision.

A local SQLite-backed design is a natural fit with the current Python runtime, but the invariant matters more than the technology choice.

Persistence should be versionable enough that future schema changes do not silently corrupt old runs.

---

# Part VII — Failure Classification and Recovery

## 20. Failure Taxonomy

Walter must classify failure before choosing recovery.

Required classes include:

- `BAD_OUTPUT`
- `MISSING_EVIDENCE`
- `CONSTRAINT_VIOLATION`
- `TASK_AMBIGUITY`
- `DEPENDENCY_FAILURE`
- `TOOL_FAILURE`
- `PROVIDER_FAILURE`
- `TIMEOUT`
- `CAPABILITY_UNAVAILABLE`
- `UNSUPPORTED_CAPABILITY`
- `REPEATED_BAD_OUTPUT`

These may coexist with broader operator-facing groupings in existing doctrine.

---

## 21. Recovery Routing

Different failures require different corrective actions.

Examples:

```text
BAD_OUTPUT
→ targeted revision if worker fit is still reasonable

MISSING_EVIDENCE
→ request evidence or assign research/reviewer lane

TASK_AMBIGUITY
→ rewrite task packet before retrying

DEPENDENCY_FAILURE
→ block downstream work and reopen/fix upstream dependency

TOOL_FAILURE
→ repair tool/runtime path or escalate if capability is missing

PROVIDER_FAILURE
→ bounded controlled retry when transient

REPEATED_BAD_OUTPUT
→ replace worker, split task, revise acceptance criteria, or replan
```

Blind identical retries are prohibited.

Valid partial work should be preserved whenever possible.

Default same-worker revision behavior should remain bounded. Existing Walter doctrine uses two failed revision cycles before reassessment; retain that as the default unless later empirical evidence justifies change.

---

# Part VIII — Replanning

## 22. Replan Model

Replanning is a structured plan mutation, not a free-form prompt side effect.

Replan triggers may include:

- invalidated assumptions;
- impossible dependency;
- newly discovered required work;
- capability constraints;
- changed external conditions;
- worker output revealing a deeper architecture issue;
- human scope change.

A `ReplanProposal` should capture:

- trigger;
- evidence;
- current plan revision;
- proposed modifications;
- tasks added/removed/reopened/blocked;
- dependency changes;
- risk implications;
- whether human approval is required.

Replan count must be bounded to prevent oscillation and architectural churn.

The Manager may dynamically replan autonomously for low-impact reversible changes consistent with the accepted objective.

Material objective changes or extraordinary authority changes remain approval-gated.

---

# Part IX — Capability Model

## 23. Capability Profiles

The current runtime's simple `model_only` / `web_search` policy is a valid v0 foundation. The bootstrap should evolve it into richer, enforceable profiles.

Required conceptual profiles:

### `model_only`

For reasoning, drafting, decomposition, critique, synthesis, planning, and other work requiring no external data or actions.

### `researcher`

For current or externally verifiable public information.

Capabilities may include bounded web search/retrieval while remaining read-only.

### `repo_reader`

For inspecting repository files, diffs, history, tests, and architecture without write authority.

### `developer_sandbox`

For implementation work inside a designated isolated workspace.

This profile is intentionally powerful **inside the sandbox** and intentionally powerless outside it.

### `reviewer`

For independent evaluation of submitted artifacts, diffs, tests, and acceptance criteria without authorship authority or promotion authority.

---

## 24. Capability Escalation

A worker that needs additional capability must produce a structured request.

The system should evaluate:

- requested capability;
- reason;
- affected task;
- risk;
- whether the request is within Manager authority;
- whether human approval is required.

The worker must not receive the capability until escalation succeeds.

Capability changes must be recorded.

---

# Part X — Developer Sandbox and Workspace Isolation

## 25. No In-Place Self-Modification

The running Walter process must never directly modify the live checkout from which it is executing.

This is a permanent self-development boundary.

Candidate development occurs in an isolated worktree or equivalent isolated workspace.

Stable Walter remains untouched during candidate construction.

---

## 26. What `developer_sandbox` Must Actually Permit

A developer worker must be capable enough to perform real software development inside its assigned workspace.

Appropriate bounded capabilities may include:

- reading repository files;
- writing files inside the assigned worktree;
- creating/deleting files inside that worktree;
- running tests;
- running static checks/build commands;
- inspecting Git diff/status;
- producing patches or commits on the candidate branch if the architecture chooses to permit local commits.

The sandbox should not be so restrictive that Walter cannot meaningfully build software.

---

## 27. What `developer_sandbox` Must Not Permit

The worker must not gain authority to:

- write outside the assigned workspace;
- modify the live Walter checkout;
- merge into `main`;
- push externally without approval;
- modify secrets or credentials;
- change permission boundaries;
- weaken sandbox enforcement;
- rewrite self-development safeguards;
- execute destructive system operations unrelated to the bounded task.

These restrictions require code-level enforcement.

Prompt instructions alone are insufficient.

---

## 28. Workspace Grants

Each development worker should receive an explicit `WorkspaceGrant` or equivalent object containing enough information to enforce boundaries, for example:

- workspace ID;
- allowed root path;
- repository identity;
- candidate branch;
- permitted command categories;
- prohibited path roots;
- write policy;
- expiration/lifecycle state.

Every filesystem operation should resolve against the granted root before execution.

Path traversal or symlink escape must be considered in implementation and tests.

---

# Part XI — Approval Model

## 29. Approval Is a First-Class Object

Approval must not exist only as a prompt string or conversational yes/no.

An `ApprovalRequest` should include:

- approval ID;
- run ID;
- category;
- exact proposed action;
- scope;
- target;
- rationale;
- risk;
- relevant artifact/diff references;
- requested capability if applicable;
- status;
- timestamps.

Required approval categories include:

- `merge_to_main`
- `push_external`
- `deploy`
- `external_communication`
- `secret_modification`
- `permission_change`
- `safety_boundary_change`
- `resource_deletion`
- `extraordinary_replan`
- `tool_escalation` when outside Manager authority.

---

## 30. Approvals Must Be Scoped

This is a critical bootstrap requirement.

An approval authorizes a **specific proposed action or bounded class of action**, not permanent generalized authority.

Example:

```text
Approved:
Merge candidate commit abc123 from branch candidate/run-42 into main
```

is materially different from:

```text
Walter may merge future changes whenever it wants
```

If the material action changes after approval, the system must require a new approval.

Examples of changes that should invalidate an approval include:

- different candidate commit;
- additional files with materially different effects;
- changed target branch;
- expanded permission scope;
- added destructive behavior;
- altered deployment target.

Approved, rejected, expired, or superseded approvals must remain auditable.

---

# Part XII — Independent Review

## 31. Self-Development Requires Independent Evaluation

Candidate Walter must never be trusted merely because Walter created it.

The safe chain is:

```text
Stable Walter N
    ↓
Candidate Walter N+1
    ↓
Automated validation
    ↓
Independent review
    ↓
Manager acceptance decision
    ↓
Human promotion approval
    ↓
Stable Walter N+1
```

This structure should remain even as Walter becomes more capable.

---

## 32. Reviewer Independence Rules

For material self-development changes:

- the authoring worker may not be the independent reviewer;
- review must use a fresh worker/runtime instance;
- reviewer context should include the candidate artifact/diff, acceptance criteria, required upstream context, and validation evidence;
- reviewer should not merely inherit the author's reasoning or conclusion;
- reviewer cannot promote the candidate;
- reviewer output remains provisional until the Manager records the acceptance decision.

Review independence is about avoiding circular self-certification, not pretending models are independent legal entities.

---

## 33. Risk-Based Review

Independent reviewers should be created when risk or verification difficulty warrants them.

Triggers include:

- self-development;
- security or safety changes;
- permission changes;
- difficult-to-verify correctness;
- externally visible material changes;
- irreversible consequences;
- low confidence;
- conflicting worker results;
- historically weak worker performance.

Routine low-risk work does not require ritualistic reviewer proliferation.

---

# Part XIII — Concurrency

## 34. Safe Parallelism

Walter should optimize for **maximum safe concurrency**, not maximum agent count.

Phase 1 should remain conservative.

Recommended semantics:

- independent model-only work may run concurrently;
- independent research/read-only tasks may run concurrently;
- overlapping writes must be serialized or isolated into separate workspaces;
- dependency conditions always override concurrency;
- high-risk operations should remain sequential and inspectable.

The existing doctrine's default active-worker cap may remain a policy setting rather than a hard architectural constant.

---

# Part XIV — Functional Requirements

## 35. Manager Planning Requirements

The Manager must be able to:

- accept a user objective;
- define completion criteria;
- identify assumptions and risks;
- decompose into specialist tasks;
- create an explicit task graph;
- attach acceptance criteria;
- assign capability profiles;
- decide which tasks may execute concurrently.

---

## 36. Manager Execution Requirements

The Manager must be able to:

- enqueue eligible tasks;
- delegate tasks;
- track task status;
- enforce dependencies;
- process worker results;
- create artifact records;
- trigger programmatic validation;
- request independent review;
- request revisions;
- replace workers;
- block downstream work when upstream state changes;
- pause for approval when required;
- stop only when completion semantics are satisfied.

---

## 37. Manager Quality Requirements

The Manager must be able to:

- evaluate artifacts against acceptance criteria;
- distinguish evidence from assertions;
- detect missing evidence or downgraded outputs;
- require domain-appropriate verification;
- reject self-acceptance;
- classify failures;
- select recovery actions;
- commission adjudication when specialist results materially conflict.

---

## 38. Manager Replanning Requirements

The Manager must be able to:

- detect invalid assumptions;
- propose explicit replan changes;
- preserve revision history;
- reopen or block affected tasks;
- update dependencies safely;
- avoid infinite replan loops;
- request approval only when the replan exceeds standing authority.

---

## 39. Manager Safety Requirements

The Manager must be able to:

- prevent workers from redefining the objective;
- prevent unauthorized capability grants;
- prevent workers from accepting their own work;
- prevent sandbox escape;
- prevent live self-modification;
- require scoped approval for consequential actions;
- preserve a durable event history of significant changes.

---

# Part XV — Suggested APIs

## 40. Manager / Orchestration Methods

The final implementation need not use these exact names, but should provide equivalent seams:

```text
create_run(objective, constraints)
generate_plan(run)
build_task_graph(plan)
create_task(...)
refresh_readiness(run)
schedule_task(task)
delegate_task(task)
record_submission(task, result)
evaluate_submission(task, artifact)
classify_failure(task, failure)
decide_recovery(task, failure)
propose_replan(run, trigger)
apply_replan(proposal)
request_approval(...)
record_approval_decision(...)
complete_run_if_ready(run)
```

---

## 41. State Methods

```text
can_transition(task, new_state)
transition(task, new_state, reason)
is_ready(task)
block_task(task, reason)
reopen_task(task, reason)
unblock_dependents(task)
mark_failed(task, failure)
```

---

## 42. Artifact Methods

```text
create_artifact(task, ...)
record_validation(artifact, ...)
record_review(artifact, ...)
accept_artifact(artifact, decision)
reject_artifact(artifact, reason)
supersede_artifact(old_artifact, new_artifact)
```

---

## 43. Capability and Workspace Methods

```text
assign_capability_profile(task, profile)
request_capability(task, capability)
escalate_capability_request(...)
enforce_workspace_boundary(path, workspace_grant)
create_candidate_workspace(...)
inspect_candidate_diff(...)
cleanup_workspace(...)
```

---

# Part XVI — Revised Bootstrap Implementation Sequence

## 44. Milestone 0 — Repository Reconciliation

Before adding major new behavior:

- inspect current runtime and contracts;
- identify reusable constructs;
- preserve functioning Agents SDK/OpenRouter/CLI behavior;
- identify documentation drift;
- define the canonical task state vocabulary;
- write an implementation map from current modules to target components.

Do not rewrite the repository merely to make it look cleaner.

---

## 45. Milestone 1 — Manager Orchestration Kernel

Build the deterministic core.

Deliverables:

- durable `Run` model;
- `WorkPlan` model;
- `TaskNode` model;
- canonical state machine;
- dependency tracking;
- acceptance logic;
- bounded revision/retry logic;
- failure taxonomy and recovery routing;
- explicit replan support;
- orchestration unit tests.

At this stage, model behavior should be mockable and the orchestration core should be testable independently.

---

## 46. Milestone 2 — Durable State, Event, and Artifact Foundation

This milestone is now required **before** self-build capability.

Deliverables:

- operational state store separate from conversation history;
- structured event store;
- artifact registry;
- artifact lineage/versioning basics;
- decision records;
- approval records;
- reload/recovery path;
- persistence tests.

This milestone establishes the audit substrate Walter will later rely on while modifying itself.

---

## 47. Milestone 3 — Capability and Approval Framework

Deliverables:

- enforceable capability profiles;
- capability request/escalation protocol;
- scoped approval requests;
- approval decisions;
- denial behavior;
- audit events for permission changes;
- tests proving workers cannot silently gain authority.

This phase should evolve the current `model_only` and web-enabled behavior rather than breaking it unnecessarily.

---

## 48. Milestone 4 — Developer Sandbox

Deliverables:

- isolated candidate worktree/workspace creation;
- explicit workspace grants;
- bounded read/write operations;
- controlled test/build command execution;
- path boundary enforcement;
- live-checkout write protection;
- Git diff/status inspection;
- candidate branch lifecycle;
- sandbox escape tests.

Do not merge candidate work into `main` in this milestone.

---

## 49. Milestone 5 — Validation and Independent Review

Deliverables:

- programmatic acceptance checks;
- reviewer worker profile;
- author/reviewer separation;
- review records;
- Manager acceptance after review;
- high-risk review policy;
- tests proving a candidate cannot self-certify.

---

## 50. Milestone 6 — Self-Build Readiness Validation

This milestone tests the machinery without crossing the self-building boundary.

Walter should demonstrate that it can:

- create a development-oriented run;
- construct a plan and task graph;
- create an isolated candidate workspace;
- delegate a bounded development task using mocked or deliberately harmless fixture work;
- preserve events and artifacts;
- run validation;
- commission independent review;
- create a scoped promotion approval request;
- stop before merge/push/promotion.

The bootstrap assignment ends here.

Walter's first meaningful self-development objective is a **separate next phase**.

---

# Part XVII — Testing Strategy

## 51. Unit Tests

Deterministic orchestration behavior should be heavily unit tested independently of provider behavior.

Required coverage includes:

- legal task transitions;
- illegal task transitions;
- readiness calculation;
- dependency blocking;
- acceptance evaluation;
- revision flow;
- rejection flow;
- failure classification;
- recovery routing;
- retry/revision limits;
- replan proposal/application;
- replan limit;
- approval object creation;
- approval scope matching;
- capability denial/escalation;
- workspace boundary enforcement;
- event emission;
- persistence/reload.

---

## 52. Integration Tests

Required end-to-end scenarios include:

1. valid dependency chain reaches accepted completion;
2. unmet dependency does not execute;
3. worker completion alone does not unlock dependents;
4. rejected upstream artifact keeps downstream task blocked;
5. revision succeeds inside configured limit;
6. repeated weak output causes worker reassessment/replacement;
7. different failure classes route to different recovery actions;
8. replan creates explicit revision history;
9. excessive replans stop rather than loop forever;
10. unauthorized capability request is denied or escalated;
11. approval-gated action cannot execute before approval;
12. approval for one candidate commit does not authorize a materially different candidate;
13. developer worker cannot write outside assigned workspace;
14. developer worker cannot modify live Walter checkout;
15. candidate workspace can be created, changed, tested, and inspected;
16. reviewer is distinct from author;
17. operational state survives process restart/reload;
18. events and artifact lineage survive reload;
19. run cannot report success while required artifacts remain unaccepted;
20. promotion flow stops at human approval gate.

---

## 53. Mocking Strategy

Model/provider calls should be mocked wherever practical.

The orchestration system must not require live OpenRouter credits to prove state-machine correctness, dependency semantics, persistence, permission enforcement, or approval behavior.

Live provider smoke tests should remain explicit opt-in checks.

---

## 54. Eval Strategy

Use eval cases for behavior that depends on Manager judgment rather than purely deterministic code.

Useful eval themes include:

- Manager does not do specialist work itself when delegation is required;
- Manager refuses worker self-acceptance;
- Manager detects weak evidence;
- Manager chooses reviewer/adjudicator appropriately;
- Manager replans when assumptions fail;
- Manager resists scope expansion from worker output;
- Manager does not treat external content as authority over task instructions;
- Manager requests approval at the correct boundary.

---

# Part XVIII — Definition of Self-Build Readiness

## 55. Required Acceptance Gate

Walter is self-build-ready only when **all** of the following have been implemented and demonstrated:

### Run and planning

- explicit durable run model exists;
- WorkPlan creation works;
- completion criteria are structured;
- revision history is preserved;
- task graph is explicit.

### Task orchestration

- one canonical task state machine exists;
- invalid transitions are rejected;
- dependency gating works;
- tasks cannot run before readiness;
- accepted outputs alone unlock downstream work.

### Acceptance and QA

- worker result is provisional;
- worker cannot accept its own work;
- programmatic acceptance gates can run;
- independent review can be commissioned;
- Manager records final acceptance decisions.

### Failure and replanning

- failure classification exists;
- recovery differs by failure type;
- blind identical retries are prevented;
- revisions are bounded;
- explicit replanning exists;
- replans are bounded and auditable.

### Persistence and observability

- operational state is durable outside conversation history;
- structured events are durable;
- artifacts have provenance and lineage;
- decisions are recorded;
- approvals are recorded;
- run state can be reloaded after interruption.

### Capabilities and isolation

- capability profiles are enforced;
- worker tool grants are least privilege;
- escalation is explicit;
- developer worker can perform useful work inside a bounded workspace;
- developer worker cannot escape its workspace;
- live Walter checkout is protected from candidate writes.

### Approval and promotion safety

- high-impact actions require first-class approval;
- approvals are scoped to specific proposed actions;
- materially changed actions require new approval;
- candidate Walter cannot promote itself;
- merge/push/deploy remain gated.

### Compatibility and verification

- current CLI behavior still works or has a documented compatible migration;
- existing runtime/provider foundations remain functional;
- unit and integration tests pass;
- live provider tests remain opt-in;
- documentation reflects actual executable semantics.

When these conditions are met, Walter may receive his first real self-development objective.

Not before.

---

# Part XIX — First Self-Build Boundary

## 56. What Bootstrap Development Builds

Bootstrap development builds the machinery that makes self-development governable.

The bootstrap assignment should end with:

- orchestration kernel;
- durable state;
- event and artifact systems;
- capability enforcement;
- sandbox/worktree isolation;
- independent review machinery;
- scoped approvals;
- tests proving the boundaries.

## 57. What Walter Builds Next

After the bootstrap passes review, Walter may be given a separate objective to produce its first candidate self-improvement.

That candidate must travel through the full system Walter now manages:

```text
Objective
→ WorkPlan
→ Task graph
→ Isolated worker execution
→ Candidate artifact
→ Automated validation
→ Independent review
→ Manager acceptance
→ Scoped human promotion approval
```

This is the moment Walter begins controlled self-building.

The bootstrap itself should not cross that line.

---

# Part XX — Current Runtime Compatibility

## 58. Preserve the Existing Foundation

The bootstrap should extend rather than casually replace the existing runtime foundation:

- Python;
- OpenAI Agents SDK;
- OpenRouter;
- current manager/worker model configuration;
- Pydantic contracts;
- `TaskPacket` / `WorkerResult` semantics where compatible;
- SQLiteSession for conversation continuity;
- CLI behavior;
- pytest;
- existing eval philosophy.

The current runtime already proves the Manager → temporary specialist → structured result loop.

The bootstrap transforms that loop into a durable orchestration system.

---

## 59. Documentation Reconciliation

Implementation work should eliminate semantic drift between documentation and runtime.

At minimum inspect and reconcile:

- simplified old task-state names versus the canonical new state machine;
- existing capability documentation versus actual available tools;
- `AGENTS_SDK.md` descriptions of worker capability;
- current task/result templates versus evolved Pydantic models;
- any doctrine that conflicts with machine-enforced behavior.

Do not rewrite Walter's philosophy merely for stylistic uniformity.

Correct contradictions and stale descriptions.

---

# Part XXI — Risks and Mitigations

## 60. Manager Prompt Becomes Too Large

**Risk:** More orchestration policy is pushed into natural-language instructions until the prompt becomes fragile.

**Mitigation:** Move deterministic control logic into typed models and executable orchestration code. Keep prompts focused on reasoning and judgment.

---

## 61. Operational State and Conversation History Blur Together

**Risk:** Walter appears persistent but cannot reliably reconstruct execution after interruption.

**Mitigation:** Maintain a dedicated operational state store with explicit entities and events.

---

## 62. Replanning Becomes Uncontrolled

**Risk:** Walter repeatedly rewrites the plan instead of completing work.

**Mitigation:** Require structured triggers, evidence, revision history, and bounded replan counts.

---

## 63. Acceptance Becomes Ceremonial

**Risk:** Every worker submission is effectively accepted automatically.

**Mitigation:** Require explicit acceptance evaluation, programmatic checks where possible, reviewer thresholds, and canonical promotion only after acceptance.

---

## 64. Workers Widen Their Own Authority

**Risk:** A worker asks for or accesses tools outside its intended lane.

**Mitigation:** Construct tools from capability profiles, enforce workspace boundaries in code, and require logged escalation.

---

## 65. Sandbox Exists Only on Paper

**Risk:** A `developer_sandbox` label is added without meaningful filesystem or command isolation.

**Mitigation:** Implement explicit workspace grants, canonical path validation, escape tests, and live-checkout protection.

---

## 66. Candidate Walter Self-Certifies

**Risk:** The same worker authors and approves the change, creating circular trust.

**Mitigation:** Separate author and reviewer, run automated validation, retain Manager acceptance, and require human promotion approval.

---

## 67. Approval Becomes Permanent Authority

**Risk:** One human approval is interpreted as standing permission for future materially different actions.

**Mitigation:** Bind approval to concrete action scope and require reapproval when scope changes.

---

## 68. Event/Artifact Infrastructure Is Added Too Late

**Risk:** Walter begins modifying itself before the system can reliably record provenance, decisions, and promotion gates.

**Mitigation:** Build durable events, artifacts, and operational state before the developer sandbox is used for real self-development.

---

# Part XXII — Long-Term Product Vision

## 69. Future Layers

After the orchestration core has proven trustworthy, Walter can expand toward:

- orchestration API;
- local control panel;
- run dashboards;
- background/long-running execution;
- richer event-store analytics;
- multi-model routing;
- project-level memory and retrieval;
- desktop companion tooling;
- mobile companion surfaces for remote status, approvals, alerts, and project progress.

These are downstream products built on the orchestration substrate.

They should not distract from bootstrap correctness.

---

# Part XXIII — Engineering Definition of Done

## 70. Bootstrap Completion

The bootstrap implementation is complete when:

- Manager orchestration works end-to-end;
- state transitions are enforced by code;
- dependencies are enforced;
- worker completion is distinct from acceptance;
- canonical project state only receives accepted artifacts;
- failure classification drives bounded recovery;
- explicit replanning works;
- durable operational persistence works;
- structured events and artifact provenance exist;
- capability profiles are enforced;
- approval objects are first-class and scoped;
- candidate development occurs only in isolated workspaces;
- live Walter cannot modify itself in place;
- automated validation can run;
- independent review is enforceable;
- human approval remains required for candidate promotion;
- tests prove these properties;
- implementation remains on a reviewable branch/worktree until the human chooses promotion.

The system is **not** complete merely because the code compiles or workers can edit files.

It is complete when Walter's self-development boundary is observable, enforceable, restart-safe, and reviewable.

---

# Part XXIV — Final Architecture Summary

Walter should become a controlled software organization, not an unrestricted autonomous agent.

The correct architecture is therefore:

```text
Human Authority
      ↓
Walter Manager
      ↓
Orchestration Core
      ↓
Task Graph + State Machine
      ↓
Temporary Least-Privilege Workers
      ↓
Candidate Artifacts
      ↓
Validation + Independent Review
      ↓
Manager Acceptance
      ↓
Canonical Project State
      ↓
Scoped Human Approval for High-Impact Promotion
```

Wrapped around the entire system:

```text
Durable Operational State
Structured Event History
Artifact Provenance and Lineage
Failure/Recovery Records
Approval Records
Workspace Boundaries
```

The core rule remains:

> **Walter may become increasingly capable, but capability must grow inside explicit authority, state, evidence, review, and promotion boundaries.**

When those boundaries are implemented and proven, Walter is ready to begin building candidate versions of itself.

That is the bootstrap target.
