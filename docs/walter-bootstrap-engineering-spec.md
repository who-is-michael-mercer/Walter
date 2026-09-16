# Walter Bootstrap Engineering Spec

## Objective

This document defines the engineering work required to transform Walter from a delegated-task agent into a Manager-owned orchestration runtime with explicit task dependencies, guardrails, artifact review, bounded retries, replan logic, safe concurrency, and approval gates.

This is the implementation-focused specification for Phase 1 and the foundation for later capability and self-improvement work.

---

## 1. Scope

### In Scope

- Manager-controlled run model
- Work plan generation
- Explicit dependency graph
- Task lifecycle state machine
- Task acceptance and review flow
- Failure classification and recovery policy
- Dynamic replanning with audit trail
- Conservative concurrency model for Phase 1
- Approval request model for high-impact actions
- Unit and integration tests for orchestration logic
- Preservation of existing model and CLI contracts where possible

### Out of Scope

- GUI or web control panel
- mobile client
- multi-model routing
- long-running service architecture
- remote / secure mode
- broad provider expansion
- unrelated repo tooling

---

## 2. Constraints

The implementation must preserve the current runtime foundation:

- Python
- OpenAI Agents SDK
- OpenRouter
- Kimi K3
- Pydantic contracts
- SQLiteSession
- CLI behavior
- pytest

The work should extend the current architecture rather than replace it wholesale.

---

## 3. Required Architecture Components

### 3.1 Run Model

Add a durable run representation.

Required fields:

- id
- objective
- constraints
- status
- plan
- tasks
- accepted_artifacts
- decisions
- unresolved_issues
- events
- final_result
- timestamps

Implementation expectation:

- Serializable to JSON or dict
- Stored in session/project state or a local state file
- Included in the event log
- Exposed to orchestration logic

### 3.2 WorkPlan

Add a structured planning object.

Required fields:

- objective
- completion_criteria
- tasks
- assumptions
- risks
- status
- revision_count
- revision_history

Implementation expectation:

- The Manager generates a WorkPlan from the objective.
- The Manager updates the plan explicitly when assumptions change.
- Revisions are logged as decisions.

### 3.3 TaskNode

Add a task model with explicit role, objective, acceptance criteria, dependencies, and execution state.

Required fields:

- id
- role
- objective
- deliverable
- context
- required_inputs
- constraints
- acceptance_criteria
- dependencies
- tool_policy
- status
- attempts
- max_attempts
- worker
- result
- timestamps

Implementation expectation:

- Task state is controlled by orchestration logic.
- Dependency validity is checked before scheduling.
- Task transitions are validated by a state machine.

### 3.4 State Machine

Create a central state machine for task transitions.

Allowed transitions must be explicit.

Example state set:

- PLANNED
- READY
- DELEGATED
- RUNNING
- SUBMITTED
- REVIEWING
- ACCEPTED
- REVISION_REQUIRED
- REPLACED
- BLOCKED
- FAILED

Implementation expectation:

- No task transition is allowed outside the state machine.
- State changes are logged as events.
- Invalid transitions raise errors.

### 3.5 Acceptance Model

Separate task completion from task acceptance.

Required flow:

- worker submits candidate artifact
- run acceptability checks
- if programmatic criteria fail, task is revision-required
- if judgment criteria remain, task enters review
- manager decides ACCEPT / REVISE / REJECT / REPLACE
- only accepted outputs unblock dependents or enter canonical state

Implementation expectation:

- A worker cannot mark their own task as accepted.
- The manager owns acceptance decisions.

### 3.6 Failure Classification Model

Add a failure taxonomy with recovery routing.

Required failure classes:

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

Implementation expectation:

- Each failure class maps to a recovery action.
- Recovery is not blind retry.
- Recovery actions are recorded in decisions/events.

### 3.7 Replan Model

Add support for explicit replanning.

Required behavior:

- trigger on evidence of invalid assumptions or unsatisfied constraints;
- propose plan changes explicitly;
- log the decision and reasons;
- enforce bounded replan count.

Implementation expectation:

- replan proposal is created before execution;
- replan is not silent;
- run keeps revision history.

### 3.8 Approval Model

Add an approval request structure for high-impact actions.

Required categories:

- merge_to_main
- push_external
- deploy
- external_communication
- secret_modification
- permission_change
- safety_boundary_change
- resource_deletion
- extraordinary_replan
- tool_escalation

Implementation expectation:

- approval is not just a prompt string; it is a first-class object;
- approved actions are logged;
- rejected or deferred approvals keep the run paused or re-routed.

### 3.9 Capability Profiles

Add capability profiles with least-privilege enforcement.

Required profiles:

- model_only
- researcher
- repo_reader
- developer_sandbox
- reviewer

Implementation expectation:

- workers receive only allowed tools;
- tool requests outside the profile require explicit escalation;
- approval is recorded for escalations.

---

## 4. Functional Requirements

### 4.1 Manager Planning

The Manager must be able to:

- accept a user objective;
- define completion criteria;
- decompose the objective into specialist tasks;
- create an explicit task graph;
- attach acceptance criteria to each task;
- assign a capability profile to each task.

### 4.2 Manager Execution

The Manager must be able to:

- enqueue eligible tasks;
- delegate tasks to workers;
- track task status;
- wait on dependencies before scheduling dependents;
- process worker results;
- request revisions when needed;
- block progress when upstream tasks fail;
- stop the run only when required deliverables are accepted.

### 4.3 Manager Quality Control

The Manager must be able to:

- evaluate artifacts against acceptance criteria;
- detect downgraded or invalid outputs;
- request human review when needed;
- classify failures before taking recovery action;
- reject or replace weak work.

### 4.4 Manager Replanning

The Manager must be able to:

- detect when a task or plan assumption is invalid;
- propose a concrete replan;
- maintain revision history;
- mark affected tasks as blocked or reopened;
- avoid infinite replanning loops.

### 4.5 Manager Safety

The Manager must be able to:

- refuse to allow workers to redefine the objective;
- refuse unauthorized tool grants;
- reject self-acceptance by workers;
- require approval for high-impact actions;
- maintain an event history of all significant changes.

---

## 5. Data Model Requirements

### 5.1 Core Types

Implementation should include or adapt these models:

- Run
- WorkPlan
- TaskNode
- Artifact
- Decision
- Event
- ApprovalRequest
- CapabilityProfile
- ReplanProposal
- WorkerFailure
- AcceptanceDecision

### 5.2 Validation

All state transitions should be validated through code.

Examples:

- a task cannot go from ACCEPTED to RUNNING;
- a task cannot be accepted without all required dependencies accepted;
- a task cannot be delegated without a worker assignment;
- a plan cannot revise itself silently;
- tool escalation without approval is forbidden.

---

## 6. Required APIs / Methods

### 6.1 Manager Methods

The manager should provide methods such as:

- create_run(objective, constraints)
- generate_plan(objective)
- build_task_graph(plan)
- schedule_task(task)
- delegate_task(task)
- evaluate_submission(task, artifact)
- classify_failure(task, failure)
- decide_recovery(task, failure)
- propose_replan(run, trigger)
- execute_replan(proposal, option)
- complete_run_if_ready(run)

### 6.2 State Methods

- can_transition(task, new_state)
- transition(task, new_state, reason)
- is_ready(task)
- unblock_dependents(task)
- mark_failed(task, reason)

### 6.3 Tool and Capability Methods

- assign_capability_profile(task, profile)
- request_tool(task, tool_name)
- escalate_tool_request(task, tool_name)
- approve_tool_escalation(task, tool_name)
- enforce_workspace_boundary(file_path, worker_id)

### 6.4 Artifact Methods

- create_artifact(task, content, type)
- accept_artifact(artifact)
- reject_artifact(artifact, reason)
- supersede_artifact(old_artifact, new_artifact)

---

## 7. Execution Semantics

### 7.1 Task Execution Order

The system should schedule tasks as follows:

- task is created in PLANNED
- task becomes READY when dependencies are satisfied
- task is DELEGATED to a worker
- task runs under its capability profile
- worker produces candidate artifact
- task becomes SUBMITTED
- manager evaluates acceptance criteria
- accepted output unblocks dependents
- rejected or failed outputs trigger recovery or replanning

### 7.2 Dependency Semantics

A task cannot run until all dependencies are ACCEPTED.

If an upstream task is rejected or fails, downstream tasks remain BLOCKED.

### 7.3 Completion Semantics

A run is complete only when all required tasks are accepted and no required artifacts remain unaccepted.

A run is not complete when workers report success and no manager acceptance occurred.

---

## 8. Safety Requirements

### 8.1 No In-Place Self-Modification

The currently running Walter process may not directly mutate the live checkout that it is executing from.

Implementation must ensure:

- all candidate development work occurs in an isolated worktree;
- main remains untouched by the active runtime;
- reviewed candidate work must be promoted only after approval.

### 8.2 No Untrusted Self-Evaluation

A generated candidate Walter must not be trusted simply because it was produced by Walter.

Implementation must require:

- independent review;
- automated validation;
- human approval for promotion.

### 8.3 No Silent Authority Changes

A worker may not silently change tools, permissions, or authority levels.

If a worker requires a new tool or privilege, the request must be escalated through the approval model.

---

## 9. Testing Strategy

### 9.1 Unit Tests

Test all orchestration logic independently of model behavior.

Required unit tests:

- task transition validation
- dependency blocking logic
- acceptance evaluation
- task rejection and revision
- failure classification
- bounded retry logic
- replan proposal and execution
- approval request creation
- tool escalation denial or approval

### 9.2 Integration Tests

End-to-end orchestration tests should validate the full lifecycle.

Example scenarios:

- valid task chain runs to completion
- unmet dependency does not execute
- rejected upstream task blocks downstream work
- same worker revision succeeds before limit
- task replacement after repeated bad output
- replan proposal works with approval
- human approval is required for merge or secrets action

### 9.3 Mocking Strategy

Model calls should be mocked wherever practical.

This ensures orchestration logic is tested without depending on network or provider reliability.

Live provider tests should be opt-in.

---

## 10. Phase 1 Acceptance Criteria

Phase 1 is complete when the following are implemented and validated:

1. explicit run model;
2. WorkPlan creation and revision tracking;
3. explicit TaskNode model with dependencies;
4. task state machine with valid transitions only;
5. separate completion vs acceptance semantics;
6. programmatic and judgment-based acceptance criteria;
7. failure classification and bounded recovery;
8. dynamic replanning with explicit trigger and logging;
9. conservative concurrency semantics for Phase 1;
10. approval request model for high-impact actions;
11. capability profiles and least-privilege tool design;
12. passing orchestration unit and integration tests;
13. reviewed implementation branch with no merge to main.

---

## 11. Implementation Sequence

### Milestone 1 — Manager V1

Build the orchestration core only.

Deliverables:

- Run model
- WorkPlan model
- TaskNode model
- state machine
- acceptance logic
- dependency tracking
- failing and revision logic
- replan support
- orchestration tests

### Milestone 2 — Capability Framework

Add least privilege profiles and worker tool restrictions.

Deliverables:

- capability profiles
- tool escalation protocol
- request and approval objects
- permission enforcement helpers

### Milestone 3 — Developer Sandbox

Add isolated worktree execution without access to the live main branch.

Deliverables:

- worktree creation and lifecycle management
- write restrictions
- read-only main enforcement
- path boundary enforcement
- git diff and status support only

### Milestone 4 — Self-Build Validation Run

Assign Walter his first real self-development feature.

Deliverables:

- event system or artifact persistence implementation
- tests
- independent review
- human approval gate
- candidate branch created but not merged

---

## 12. Implementation Guidance

### 12.1 Before coding

- inspect current architecture;
- identify current reusable constructs;
- preserve TaskPacket and WorkerResult contracts where possible;
- keep existing runtime and provider stack stable;
- avoid changing prompts as a substitute for logic;
- design state transitions in code before adding more features.

### 12.2 During coding

- add tests in the same PR/branch as implementation;
- prefer small reviewable units;
- document state transitions and decisions;
- keep the manager orchestration logic explicit and testable;
- do not add GUI or mobile work in this branch.

### 12.3 At stop point

- stop with a reviewable branch;
- do not merge into main;
- provide a summary of architecture decisions and test coverage;
- include open risks and next-step follow-up.

---

## 13. Risks and Mitigations

### Risk: Manager prompt becomes too large and fragile

Mitigation:

- centralize state machine logic in code;
- use structured models instead of prompt-inferred logic;
- do not rely on free-form prompt reasoning for transitions.

### Risk: Replanning becomes uncontrolled

Mitigation:

- require replan triggers and explicit evidence;
- enforce max replan count per run;
- log all revisions in plan history.

### Risk: Workers widen scope or self-grant tools

Mitigation:

- enforce tool profiles;
- require escalation and approval;
- maintain audit log of delegated capabilities.

### Risk: Live runtime mutates itself

Mitigation:

- operate only in isolated worktrees;
- preserve live main as the stable runtime;
- require human approval before any promotion.

### Risk: Acceptance becomes a formality instead of a gate

Mitigation:

- require explicit acceptance evaluation; 
- use programmatic gates where possible;
- require independent review for material changes.

---

## 14. Definition of Done

The implementation is successful when:

- Manager V1 run logic works end-to-end in tests;
- the state machine is enforced by code;
- dependency gating works correctly;
- acceptance criteria are structured and enforced;
- failure classification drives recovery decisions;
- workers cannot accept their own work;
- high-impact operations pause for approval;
- work is performed in isolated worktrees;
- no live self-editing occurs;
- the branch is ready for human review.

---

## 15. Implementation Summary

Walter’s first production-grade architecture should not be a more clever chat agent. It must be a controlled work organization with explicit state, explicit dependencies, explicit reviews, explicit safety gates, and reviewable outputs.

The engineering goal is straightforward:

Build a runtime that can manage specialized workers without letting them rewrite authority, silently change project truth, or self-approve unsafe actions.

This is the foundation required before Walter can safely begin improving itself.
