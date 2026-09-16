# Walter Bootstrap Design

## Purpose

This document captures the conceptual architecture for Walter’s evolution from a delegated-task agent into a manager-led organization of temporary specialist workers. It defines the design intent, safety principles, architectural boundaries, deployment strategy, and the long-term path to safe self-improvement.

The design is intentionally conservative at first: Walter gains autonomy only after the management system, execution model, and approval controls are proven in practice.

---

## 1. Design Goal

Walter is not intended to become a permanent collection of named agents. Walter is intended to become an organization generator.

For each objective, Walter should:

- determine the minimum viable work required;
- create only the specialists needed;
- assign constraints and permissions explicitly;
- establish dependencies and completion gates;
- inspect outputs before accepting them as truth;
- maintain a durable project record;
- request human approval before high-impact actions;
- evolve only through controlled, reviewable changes.

This is the core design philosophy behind Walter’s system architecture.

---

## 2. Core Design Principles

### 2.1 Managers Own Reality

The Manager is the source of truth for the operating model of a run. It owns:

- objective definition;
- completion criteria;
- task decomposition;
- dependency graph construction;
- worker assignment;
- review decisions;
- replanning decisions;
- run completion conditions;
- escalation boundaries.

The Manager is not just a thin coordinator. It is the control plane.

### 2.2 Workers Are Temporary and Bounded

Workers should operate as temporary specialists with narrow scopes:

- one lane;
- one objective;
- one deliverable;
- one worker lifecycle;
- explicit constraints;
- shared acceptance gates.

Workers are not allowed to redefine scope, escalate authority, or decide whether their own output is accepted.

### 2.3 Completion Is Not Acceptance

A worker can submit a candidate artifact without the system accepting it as project truth.

This distinction is central to the architecture:

- completion = the worker produced a candidate output;
- acceptance = Walter evaluated the output and declared it valid.

Only accepted outputs may unblock downstream tasks or enter canonical project state.

### 2.4 Safety Is Stronger Than Cleverness

The system should always prefer:

- isolated workspaces;
- explicit artifacts;
- visible review and decision logs;
- independent validation;
- staged promotion;
- human approval for high-impact actions.

The architecture should assume that self-improvement is dangerous unless controlled aggressively.

### 2.5 Tool Access Must Be Least Privilege

Walter does not hand broad capability to every worker. Every worker receives only the tools needed for its lane.

This includes:

- capability profiles;
- bounded worktrees;
- audit logging for tool requests;
- explicit escalation paths for additional permissions.

---

## 3. Architectural Layers

Walter’s target architecture separates concerns across six layers.

### 3.1 Human Layer

Human users provide:

- objectives;
- approval decisions;
- exceptions;
- policy override when needed.

Humans are the source of final authority for high-impact actions.

### 3.2 Walter Manager Layer

The Manager owns the operating logic for a run:

- planning;
- decomposition;
- delegation;
- quality review;
- replanning;
- completion checks;
- escalation boundaries.

### 3.3 Orchestration Core

The orchestration core stores and manages the executable state of a run:

- WorkPlan
- TaskGraph
- dependency state
- task lifecycle state
- artifact status
- decisions and events

This layer should be explicit, serializable, and inspectable.

### 3.4 Worker Runtime

The worker runtime is the environment in which temporary specialists execute. It is not a permanent agent framework. It is a runtime for short-lived workers under strict constraints.

### 3.5 Artifact System

The artifact system is responsible for the progression:

Candidate → Reviewed → Accepted → Canonical

Artifacts are not just files. They are structured project outputs with provenance, validation state, and audit trail.

### 3.6 Project State

The project state persists:

- decisions;
- artifacts;
- unresolved issues;
- run history;
- canonical project records;
- constraints and approvals.

This allows Walter to continue work across sessions without reconstructing the project from conversation alone.

---

## 4. Core Run Model

Every run should have a durable representation.

Conceptually:

```python
@dataclass
class Run:
    id: str
    objective: str
    constraints: List[str]
    status: RunStatus
    plan: WorkPlan
    tasks: Dict[str, TaskNode]
    accepted_artifacts: List[Artifact]
    decisions: List[Decision]
    unresolved_issues: List[str]
    events: List[Event]
    final_result: Optional[str]
```

The run model should be the primary source of truth for the manager’s understanding of execution state.

This makes Walter observable and debuggable even at runtime.

---

## 5. Work Planning and Task Decomposition

The Manager converts a user objective into a structured plan with measurable completion criteria.

A WorkPlan includes:

- objective;
- completion criteria;
- tasks;
- assumptions;
- risks;
- status;
- revision history.

The important idea is that the plan is not static. It can evolve in response to evidence, but such revisions must be explicit and logged.

Task decomposition should favor clarity and bounded work. A task should represent a single specialist lane with a single inspectable deliverable.

---

## 6. Dependency Graph Design

Dependencies must be explicit and enforced.

A task should not be eligible to run until all required upstream tasks have been accepted.

This creates a practical graph:

- Requirements and risk analysis can run in parallel.
- Architecture waits for accepted upstream work.
- Implementation waits for architecture acceptance.
- Tests wait for implementation acceptance.
- Independent review waits for test acceptance.

This graph is a strong foundation for both correctness and concurrency control.

---

## 7. Task Lifecycle and State Management

Each task should move through a clear state machine:

PLANNED → READY → DELEGATED → RUNNING → SUBMITTED → REVIEWING → ACCEPTED / REVISION_REQUIRED / REPLACED / BLOCKED / FAILED

The state machine should be enforced by code, not by ad hoc prompting.

This makes it possible to:

- detect when a task is blocked;
- determine whether a task is actually complete;
- resume work correctly after interruptions;
- prevent illegal transitions;
- audit the run history.

---

## 8. Acceptance, Rejection, and Revision

The architecture should define clear decision gates:

- Worker submits candidate artifact.
- Manager evaluates against acceptance criteria.
- Manager accepts, rejects, requests revision, or replaces the worker.
- Only accepted artifacts can unblock downstream tasks.

This boundary is crucial. It prevents a “worker completed the task” statement from being misread as “project truth is changed.”

---

## 9. Failure Classification

Walter should classify failure before retrying.

Failure classes should include:

- BAD_OUTPUT
- MISSING_EVIDENCE
- CONSTRAINT_VIOLATION
- TASK_AMBIGUITY
- DEPENDENCY_FAILURE
- TOOL_FAILURE
- PROVIDER_FAILURE
- TIMEOUT
- CAPABILITY_UNAVAILABLE
- UNSUPPORTED_CAPABILITY
- REPEATED_BAD_OUTPUT

Not every failure should trigger the same recovery.

Examples:

- BAD_OUTPUT → same worker with targeted feedback
- TASK_AMBIGUITY → rewrite task packet
- DEPENDENCY_FAILURE → reopen upstream task
- PROVIDER_FAILURE → controlled retry
- REPEATED_BAD_OUTPUT → replace or replan

This creates a practical, auditable error recovery model.

---

## 10. Replanning Design

Replanning should be explicit, evidence-driven, and bounded.

It is not a free-form prompt side effect. It is a structured change to the run’s plan.

Replans should occur only when:

- the original assumption is invalid;
- a required dependency cannot be satisfied;
- tool or capability constraints change;
- the task shape is no longer correct;
- the worker’s output reveals a broader design issue.

There should be a replan limit per run to avoid oscillation and runaway architecture churn.

---

## 11. Concurrency and Safety

Independent tasks may run concurrently, but only under explicitly controlled limits.

For Phase 1, the system should be conservative:

- parallel read-only work is allowed;
- write operations are serialized;
- dependency conditions must be satisfied before execution;
- workers should run in isolated or bounded workspaces.

This balances throughput with correctness and observability.

---

## 12. Approval Model

Walter must distinguish between a comfortable internal decision and an externally authoritative action.

Certain actions require human approval before they are taken:

- merge into main;
- push external changes;
- deploy;
- modify secrets;
- change permission boundaries;
- change self-development safeguards;
- destructive operations.

This is not optional. It is the core safety model for a self-improving system.

---

## 13. Capability System

Absolute tool access is a design risk.

Walter should instead use capability profiles:

- model_only
- research
- repo_reader
- developer_sandbox
- reviewer

A worker should only receive the tools required for its lane. Higher-impact tools require explicit escalation and approval.

This is a foundational design principle for safe self-development.

---

## 14. Worktree Isolation and Sandbox Boundaries

Self-development should happen only in isolated worktrees.

The running Walter process must not modify its own live checkout.

This means:

- stable main remains unchanged by live runtime;
- candidate work occurs in a separate worktree branch;
- tests and review happen before any merge;
- the candidate branch must be promoted only after review and approval.

This is one of the strongest safety boundaries in the design.

---

## 15. Event Architecture

Every major orchestration change should emit a structured event.

Examples:

- run.started
- task.created
- task.ready
- task.blocked
- task.accepted
- artifact.submitted
- review.started
- review.completed
- plan.revised
- human.approval_required
- human.approved
- human.rejected

These events provide:

- auditability;
- run debugging support;
- future GUI and control panel data sources;
- a basis for regression analysis.

---

## 16. Artifact and Project Persistence

Once the system has workers and tasks, it needs durable project state.

Artifacts should have:

- provenance;
- validation status;
- acceptance state;
- versioning;
- run association;
- artifact lineage.

Project state should carry:

- objective;
- workspace;
- accepted artifacts;
- decisions;
- run history;
- unresolved issues;
- constraints.

This enables Walter to continue work later without reconstructing state from the chat history alone.

---

## 17. Safety Model for Self-Improvement

Walter may eventually generate candidate versions of itself, but there is a strict rule:

candidate Walter must not be trusted merely because Walter created it.

The safe chain is:

Stable Walter N
  → candidate Walter N+1
  → isolated environment
  → testing
  → independent evaluation
  → human approval
  → promotion

This system should remain in place even as autonomy increases.

---

## 18. Bootstrap Sequence

The progression is deliberate:

1. Human + Codex build management kernel
2. Human + Codex give Walter safe development capabilities
3. Walter manages worker runs in isolated worktrees
4. Walter produces candidate patches
5. Candidate outputs are reviewed independently
6. Human approves promotion to main
7. Walter becomes progressively more capable

This is the safe path to autonomous software construction.

---

## 19. Long-Term Product Vision

The long-term system will include:

- orchestration API;
- control panel;
- project dashboards;
- long-running background execution;
- event store and audit history;
- multi-model routing;
- desktop and mobile companion surfaces.

But those features should arrive after the orchestration architecture is proven and observable.

---

## 20. Design Success Criteria

The design succeeds when Walter can:

- decompose complex goals into tasks;
- enforce dependency ordering;
- create specialist workers with scoped capabilities;
- accept only verified outputs;
- classify and recover from failures logically;
- replan when assumptions are invalid;
- wait for necessary approvals;
- operate in isolated development workspaces;
- remain safe while building candidates of itself.

This is the design outcome worth pursuing.

---

## 21. Design Summary

Walter’s architecture should not be built as a smarter prompt wrapper. It should be built as a bounded organization system with explicit state, tool boundaries, artifact review, decision logging, and safety gates.

The key design insight is simple:

Walter’s power comes from managing work correctly, not from being capable of free-form self-authority.

The system becomes trustworthy only when its control plane is explicit, inspectable, and constrained.

That is the core architecture to build.
