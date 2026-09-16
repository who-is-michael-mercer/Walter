"""Manager-only control plane. Never expose this object as a worker tool.

Every public mutation reloads a snapshot and commits it with its events atomically.
Validation/review methods accept trusted executor evidence, never WorkerResult claims.
"""
from __future__ import annotations
import hashlib
import json
from typing import Callable
from .contracts import WorkerResult
from .models import (AcceptanceDecision, ApprovalDecision, ApprovalGate, ApprovalRequest, ApprovalStatus, Artifact,
    ArtifactValidation, CapabilityProfile, Decision, Event, FailureClass, RecoveryDecision,
    ReplanProposal, Review, Run, TaskNode, TaskStatus, WorkerAssignment, WorkerFailure,
    WorkPlan, now)
from .store import SQLiteStore


class GateError(ValueError):
    pass


TRANSITIONS = {
    TaskStatus.PLANNED: {TaskStatus.READY, TaskStatus.BLOCKED},
    TaskStatus.READY: {TaskStatus.DELEGATED, TaskStatus.BLOCKED},
    TaskStatus.DELEGATED: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.BLOCKED},
    TaskStatus.RUNNING: {TaskStatus.SUBMITTED, TaskStatus.FAILED, TaskStatus.BLOCKED},
    TaskStatus.SUBMITTED: {TaskStatus.REVIEWING, TaskStatus.FAILED},
    TaskStatus.REVIEWING: {TaskStatus.ACCEPTED, TaskStatus.REVISION_REQUIRED, TaskStatus.REPLACED, TaskStatus.FAILED},
    TaskStatus.REVISION_REQUIRED: {TaskStatus.DELEGATED, TaskStatus.BLOCKED},
    TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.REPLACED},
    TaskStatus.FAILED: {TaskStatus.READY, TaskStatus.REVISION_REQUIRED, TaskStatus.REPLACED},
    TaskStatus.ACCEPTED: set(), TaskStatus.REPLACED: set(), TaskStatus.CANCELLED: set(),
}


def _scope(scope: dict) -> tuple[str, str]:
    value = json.dumps(scope, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return value, hashlib.sha256(value.encode()).hexdigest()


class Orchestrator:
    def __init__(self, store: SQLiteStore, *, manager_id: str = "manager"):
        if not manager_id.strip():
            raise ValueError("Configured manager authority must be substantive")
        self.store = store
        self.manager_id = manager_id

    def get_run(self, run_id: str) -> Run:
        return self.store.load(run_id)

    inspect = get_run

    def _mutate(self, run_id: str, operation: Callable):
        run = self.get_run(run_id)
        if run.status != "active":
            raise GateError("Run is terminal")
        events = []
        result = operation(run, events)
        self.store.save(run, events, run.version)
        return result

    @staticmethod
    def _event(run, events, kind, **data):
        events.append(Event(run_id=run.id, kind=kind, data=data))

    def _transition(self, run, events, task, status, reason):
        if status not in TRANSITIONS[task.status]:
            raise GateError(f"Illegal transition {task.status} -> {status}")
        previous = task.status
        task.status = status
        task.updated_at = now()
        self._event(run, events, "task."+status.value.lower(), task_id=task.id, previous=previous.value, reason=reason)

    def create_run(self, objective: str, completion_criteria: list[str], *, constraints: list[str] | None = None, max_replans: int = 3) -> Run:
        if not objective.strip() or not all(x.strip() for x in completion_criteria):
            raise GateError("Objective and criteria must be substantive")
        run = Run(objective=objective, constraints=constraints or [], plan=WorkPlan(objective=objective, completion_criteria=completion_criteria, max_replans=max_replans))
        return self.store.save(run, [Event(run_id=run.id, kind="run.created")], None)

    @staticmethod
    def _graph(run):
        visiting, visited = set(), set()
        def visit(key):
            if key in visiting:
                raise GateError("Dependency cycle")
            if key in visited:
                return
            visiting.add(key)
            for dep in run.tasks[key].packet.dependencies:
                if dep in run.tasks:
                    if run.tasks[dep].status in {TaskStatus.CANCELLED, TaskStatus.REPLACED}:
                        raise GateError("Dependency references retired task")
                    visit(dep)
                elif dep not in run.artifacts:
                    raise GateError(f"Unknown dependency {dep}")
            visiting.remove(key)
            visited.add(key)
        for key, task in run.tasks.items():
            if task.status not in {TaskStatus.CANCELLED, TaskStatus.REPLACED}:
                visit(key)

    def _ready(self, run, task):
        for dep in task.packet.dependencies:
            if dep in run.tasks:
                if run.tasks[dep].status != TaskStatus.ACCEPTED:
                    return False
            elif dep not in run.accepted_artifacts:
                return False
        if any(value not in run.available_inputs and value not in run.accepted_artifacts for value in task.packet.required_inputs):
            return False
        if task.capability == CapabilityProfile.DEVELOPER_SANDBOX and not task.workspace_id:
            return False
        # A bare approval ID is ambiguous and cannot authorize task execution.
        if task.approval_ids:
            return False
        for gate in task.approval_gates:
            request = run.approvals.get(gate.request_id)
            decision = run.approval_decisions.get(gate.request_id)
            if (not request or request.status != ApprovalStatus.APPROVED or not decision or
                    not decision.approved or request.action != gate.action or
                    request.scope_digest != gate.scope_digest or request.scope_json != gate.scope_json):
                return False
        return bool(task.packet.acceptance_criteria)

    def _refresh(self, run, events):
        for task in run.tasks.values():
            if task.status == TaskStatus.PLANNED and self._ready(run, task):
                self._transition(run, events, task, TaskStatus.READY, "Dependencies and input gates satisfied")
            elif (task.status == TaskStatus.BLOCKED and task.blocker in
                    {"Capability prerequisites missing", "Approval prerequisites satisfied"} and self._ready(run, task)):
                task.blocker = None
                self._transition(run, events, task, TaskStatus.READY, "Capability prerequisites satisfied")

    def set_completion_criteria(self, run_id: str, criteria: list[str]):
        def operation(run, events):
            if not criteria or not all(c.strip() for c in criteria) or any(t.attempts for t in run.tasks.values()):
                raise GateError("Completion criteria must be defined before execution")
            run.plan.completion_criteria = list(criteria)
            self._event(run, events, "plan.criteria_defined", criteria=criteria)
        self._mutate(run_id, operation)

    def resume(self, run_id: str) -> Run:
        """Explicit interruption recovery, without automatically rerunning a worker."""
        def operation(run, events):
            for task in run.tasks.values():
                if task.status in {TaskStatus.DELEGATED, TaskStatus.RUNNING}:
                    failure = WorkerFailure(task_id=task.id, classification=FailureClass.TIMEOUT, evidence="Assignment interrupted before durable submission")
                    run.failures.append(failure)
                    self._transition(run, events, task, TaskStatus.FAILED, failure.evidence)
                    task.blocker = failure.evidence
                    self._event(run, events, "failure.classified", failure=failure.model_dump(mode="json"))
                    if task.assignment:
                        self._event(run, events, "assignment.failed", assignment_id=task.assignment.id,
                            task_id=task.id, reason=failure.evidence)
            self._event(run, events, "run.resumed", reason="Operator resumed durable run")
        self._mutate(run_id, operation)
        return self.get_run(run_id)

    def add_tasks(self, run_id: str, tasks: list[TaskNode]):
        def operation(run, events):
            if run.plan.revision or any(t.attempts for t in run.tasks.values()):
                raise GateError("Use explicit replan after execution begins")
            for source in tasks:
                task = source.model_copy(deep=True)
                if task.id in run.tasks or task.status != TaskStatus.PLANNED or task.attempts or task.artifact_ids or task.assignment:
                    raise GateError("Only fresh unique tasks can be added")
                run.tasks[task.id] = task
                run.plan.task_ids.append(task.id)
                self._event(run, events, "task.created", task_id=task.id)
            self._graph(run)
            self._refresh(run, events)
        self._mutate(run_id, operation)

    plan = add_tasks

    def register_input(self, run_id: str, name: str, reference: str):
        def operation(run, events):
            if not reference.strip() or name in run.available_inputs or name in run.tasks or name in run.artifacts:
                raise GateError("Input reference must be nonempty and immutable")
            run.available_inputs[name] = reference
            self._event(run, events, "input.registered", name=name, reference=reference)
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def bind_workspace(self, run_id: str, task_id: str, workspace_id: str):
        """Bind initial trusted sandbox grant; rebinding needs a capability approval."""
        def operation(run, events):
            task = run.tasks[task_id]
            if task.workspace_id or task.attempts or task.status not in {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.BLOCKED} or not workspace_id.strip():
                raise GateError("Workspace binding must be initial and precede delegation")
            if task.status == TaskStatus.BLOCKED and task.blocker != "Capability prerequisites missing":
                raise GateError("Workspace cannot resolve this blocker")
            task.workspace_id = workspace_id
            self._event(run, events, "workspace.bound", task_id=task_id, workspace_id=workspace_id)
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def replace_workspace(self, run_id: str, task_id: str, expected_workspace_id: str,
            new_workspace_id: str, reason: str):
        """Audit a Manager-created replacement sandbox after explicit task recovery."""
        def operation(run, events):
            task = run.tasks[task_id]
            if task.capability != CapabilityProfile.DEVELOPER_SANDBOX:
                raise GateError("Workspace replacement requires a developer sandbox task")
            if task.status not in {TaskStatus.READY, TaskStatus.REVISION_REQUIRED} or not task.attempts:
                raise GateError("Workspace can only be replaced after recovery in a safe retry state")
            if task.workspace_id != expected_workspace_id:
                raise GateError("Expected old workspace does not match persisted task state")
            if (not new_workspace_id.strip() or new_workspace_id == expected_workspace_id or
                    not reason.strip()):
                raise GateError("Replacement workspace and reason must be substantive")
            if task.artifact_ids and run.artifacts[task.artifact_ids[-1]].status == "candidate":
                raise GateError("Current candidate must be rejected through failure recovery first")
            old_workspace_id = task.workspace_id
            task.workspace_id = new_workspace_id
            task.updated_at = now()
            self._event(run, events, "workspace.replaced", task_id=task_id,
                old_workspace_id=old_workspace_id, new_workspace_id=new_workspace_id,
                reason=reason)
        self._mutate(run_id, operation)

    def reload(self, run_id: str) -> Run:
        """Load durable state; in-flight assignments stay in-flight until explicit recovery."""
        return self.get_run(run_id)

    def delegate(self, run_id: str, task_id: str, worker_id: str) -> WorkerAssignment:
        def operation(run, events):
            task = run.tasks[task_id]
            if not worker_id.strip() or worker_id == self.manager_id or not self._ready(run, task) or task.attempts >= task.max_attempts:
                raise GateError("Worker, readiness or attempt gate failed")
            if task.status not in {TaskStatus.READY, TaskStatus.REVISION_REQUIRED}:
                raise GateError("Task is not delegatable")
            assignment = WorkerAssignment(worker_id=worker_id, task_id=task_id, capability=task.capability, workspace_id=task.workspace_id)
            self._transition(run, events, task, TaskStatus.DELEGATED, "Manager delegation")
            task.assignment = assignment
            task.assignment_history.append(assignment)
            task.attempts += 1
            self._event(run, events, "assignment.created", assignment=assignment.model_dump(mode="json"), attempt=task.attempts)
            return assignment
        return self._mutate(run_id, operation)

    def start(self, run_id: str, task_id: str):
        def operation(run, events):
            task = run.tasks[task_id]
            if not self._ready(run, task):
                raise GateError("Execution gates no longer satisfied")
            self._transition(run, events, task, TaskStatus.RUNNING, "Worker started")
            self._event(run, events, "assignment.started", assignment_id=task.assignment.id,
                task_id=task.id, worker_id=task.assignment.worker_id)
        self._mutate(run_id, operation)

    def submit(self, run_id: str, task_id: str, assignment_id: str, worker_id: str,
            result: WorkerResult, *, workspace_fingerprint: str | None = None) -> Artifact:
        def operation(run, events):
            task = run.tasks[task_id]
            if (not task.assignment or task.assignment.id != assignment_id or
                    task.assignment.worker_id != worker_id):
                raise GateError("Submission does not match the current worker assignment")
            if result.task_id != task_id or result.status != "completed" or not result.deliverable.strip():
                raise GateError("Expected matching completed candidate; route blockers through fail")
            self._transition(run, events, task, TaskStatus.SUBMITTED, "Candidate received")
            if task.capability == CapabilityProfile.DEVELOPER_SANDBOX and not workspace_fingerprint:
                raise GateError("Developer candidate requires observed workspace fingerprint")
            inputs = [a for dep in task.packet.dependencies for a in (run.tasks[dep].artifact_ids[-1:] if dep in run.tasks else [dep])]
            artifact = Artifact(run_id=run_id, task_id=task_id, worker_id=worker_id, content=result.deliverable, content_digest=hashlib.sha256(result.deliverable.encode()).hexdigest(), workspace_fingerprint=workspace_fingerprint, version=len(task.artifact_ids)+1, predecessor_id=task.artifact_ids[-1] if task.artifact_ids else None, input_artifact_ids=inputs)
            task.result = result.model_copy(deep=True)
            task.artifact_ids.append(artifact.id)
            run.artifacts[artifact.id] = artifact
            self._event(run, events, "artifact.created", artifact=artifact.model_dump(mode="json"))
            self._event(run, events, "artifact.submitted", artifact_id=artifact.id, task_id=task_id, version=artifact.version)
            self._event(run, events, "assignment.completed", assignment_id=task.assignment.id,
                task_id=task.id, artifact_id=artifact.id)
            return artifact.model_copy(deep=True)
        return self._mutate(run_id, operation)

    def _candidate(self, run, events, artifact_id, workspace_fingerprint=None):
        artifact = run.artifacts[artifact_id]
        task = run.tasks[artifact.task_id]
        if hashlib.sha256(artifact.content.encode()).hexdigest() != artifact.content_digest:
            raise GateError("Candidate content changed")
        if artifact.workspace_fingerprint and artifact.workspace_fingerprint != workspace_fingerprint:
            raise GateError("Current workspace fingerprint must match candidate")
        if task.artifact_ids[-1] != artifact_id or artifact.status != "candidate":
            raise GateError("Not the current candidate")
        if task.status == TaskStatus.SUBMITTED:
            self._transition(run, events, task, TaskStatus.REVIEWING, "Manager QA started")
        if task.status != TaskStatus.REVIEWING:
            raise GateError("Task is not reviewing")
        return artifact, task

    def validate(self, run_id: str, artifact_id: str, check: str, passed: bool, evidence: str, validator_id: str, *, workspace_fingerprint: str | None = None):
        def operation(run, events):
            artifact, task = self._candidate(run, events, artifact_id, workspace_fingerprint)
            if validator_id == self.manager_id or validator_id in {a.worker_id for a in task.assignment_history}:
                raise GateError("Author cannot validate own candidate")
            record = ArtifactValidation(artifact_id=artifact_id, content_digest=artifact.content_digest, check=check, passed=passed, evidence=evidence, validator_id=validator_id)
            self._event(run, events, "artifact.validation_started", artifact_id=artifact_id,
                check=check, validator_id=validator_id)
            artifact.validations.append(record)
            self._event(run, events, "artifact.validation_completed", validation=record.model_dump())
            return record
        return self._mutate(run_id, operation)

    def review(self, run_id: str, artifact_id: str, reviewer_id: str, passed: bool, evidence: str, *, workspace_fingerprint: str | None = None):
        def operation(run, events):
            artifact, task = self._candidate(run, events, artifact_id, workspace_fingerprint)
            if reviewer_id == self.manager_id or reviewer_id in {a.worker_id for a in task.assignment_history}:
                raise GateError("Reviewer must be independent of all candidate authors")
            record = Review(artifact_id=artifact_id, content_digest=artifact.content_digest, reviewer_id=reviewer_id, passed=passed, evidence=evidence)
            artifact.reviews.append(record)
            self._event(run, events, "artifact.reviewed", review=record.model_dump())
            return record
        return self._mutate(run_id, operation)

    def accept(self, run_id: str, task_id: str, manager_id: str | None = None, reason: str = "", *, workspace_fingerprint: str | None = None):
        """Accept using configured Manager authority; caller identity is never trusted."""
        if manager_id is not None and manager_id != self.manager_id:
            raise GateError("Acceptance authority does not match configured Manager")
        def operation(run, events):
            task = run.tasks[task_id]
            if not task.artifact_ids:
                raise GateError("No candidate")
            artifact, task = self._candidate(run, events, task.artifact_ids[-1], workspace_fingerprint)
            evidence_principals = ({a.worker_id for a in task.assignment_history} |
                {v.validator_id for v in artifact.validations} | {r.reviewer_id for r in artifact.reviews})
            if self.manager_id in evidence_principals:
                raise GateError("Author cannot accept own output")
            if any(v.content_digest != artifact.content_digest for v in [*artifact.validations, *artifact.reviews]):
                raise GateError("Evidence does not match candidate content")
            checks = {v.check: v.passed for v in artifact.validations}
            if any(not checks.get(check) for check in task.required_checks) or any(not v for v in checks.values()):
                raise GateError("Validation gates failed")
            if (task.review_required or task.high_risk or task.capability == CapabilityProfile.DEVELOPER_SANDBOX) and (not artifact.reviews or not artifact.reviews[-1].passed):
                raise GateError("Independent review required")
            if not task.required_checks and not artifact.reviews:
                raise GateError("At least one external validation or review is required")
            if not self._ready(run, task):
                raise GateError("Inputs are no longer accepted")
            decision = AcceptanceDecision(action="ACCEPT", reason=reason, actor_id=self.manager_id,
                context=f"Acceptance of artifact {artifact.id} for task {task_id}",
                options_considered=["ACCEPT", "REVISE", "REJECT", "REPLACE"],
                consequences=["Artifact enters canonical state", "Accepted dependencies may become ready"],
                artifact_id=artifact.id, affected_ids=[task_id], evidence=[v.id for v in artifact.validations]+[r.id for r in artifact.reviews])
            run.acceptances.append(decision)
            run.decisions.append(decision)
            artifact.status = "accepted"
            run.accepted_artifacts.append(artifact.id)
            self._transition(run, events, task, TaskStatus.ACCEPTED, reason)
            self._event(run, events, "artifact.accepted", artifact_id=artifact.id, decision_id=decision.id)
            self._refresh(run, events)
            return decision
        return self._mutate(run_id, operation)

    def _fail(self, run, events, task, classification: FailureClass, evidence: str) -> WorkerFailure:
        failure = WorkerFailure(task_id=task.id, classification=classification, evidence=evidence)
        self._transition(run, events, task, TaskStatus.FAILED, evidence)
        task.blocker = evidence
        run.failures.append(failure)
        self._event(run, events, "failure.classified", failure=failure.model_dump(mode="json"))
        if task.assignment:
            self._event(run, events, "assignment.failed", assignment_id=task.assignment.id,
                task_id=task.id, reason=evidence)
        return failure

    def fail(self, run_id: str, task_id: str, classification: FailureClass, evidence: str) -> WorkerFailure:
        """Record a trusted Manager/system classification outside a worker callback."""
        def operation(run, events):
            return self._fail(run, events, run.tasks[task_id], classification, evidence)
        return self._mutate(run_id, operation)

    def fail_assignment(self, run_id: str, task_id: str, assignment_id: str, worker_id: str,
            classification: FailureClass, evidence: str) -> WorkerFailure:
        """Record worker execution failure only for the exact current assignment."""
        def operation(run, events):
            task = run.tasks[task_id]
            if (not task.assignment or task.assignment.id != assignment_id or
                    task.assignment.worker_id != worker_id):
                raise GateError("Failure does not match the current worker assignment")
            return self._fail(run, events, task, classification, evidence)
        return self._mutate(run_id, operation)

    def recover(self, run_id: str, failure_id: str, reason: str, *, actor_id: str = "manager") -> RecoveryDecision:
        if actor_id not in {"manager", self.manager_id}:
            raise GateError("Recovery authority does not match configured Manager")
        def operation(run, events):
            failure = next(f for f in run.failures if f.id == failure_id)
            task = run.tasks[failure.task_id]
            if any(r.failure_id == failure_id for r in run.recoveries) or task.status != TaskStatus.FAILED:
                raise GateError("Failure already recovered or superseded")
            kind = failure.classification
            action = "REPLAN"
            if kind in {FailureClass.PROVIDER_FAILURE, FailureClass.TIMEOUT}:
                action = "RETRY"
            elif kind in {FailureClass.BAD_OUTPUT, FailureClass.MISSING_EVIDENCE}:
                action = "REVISE"
            elif kind in {FailureClass.REPEATED_BAD_OUTPUT, FailureClass.CONSTRAINT_VIOLATION}:
                action = "REPLACE"
            elif kind in {FailureClass.CAPABILITY_UNAVAILABLE, FailureClass.UNSUPPORTED_CAPABILITY, FailureClass.TOOL_FAILURE}:
                action = "ESCALATE"
            if action in {"RETRY", "REVISE"} and task.attempts >= task.max_attempts:
                action = "REPLAN"
            if action == "REVISE" and task.revisions >= task.max_revisions:
                action = "REPLACE"
            if action == "RETRY":
                if not self._ready(run, task):
                    raise GateError("Retry gates unresolved")
                self._transition(run, events, task, TaskStatus.READY, reason)
                self._event(run, events, "retry.scheduled", task_id=task.id, failure_id=failure.id, next_attempt=task.attempts + 1)
            elif action == "REVISE":
                task.revisions += 1
                self._transition(run, events, task, TaskStatus.REVISION_REQUIRED, reason)
            elif action == "REPLACE":
                self._transition(run, events, task, TaskStatus.REPLACED, reason)
                self._event(run, events, "worker.replaced", task_id=task.id, failure_id=failure.id,
                    worker_id=task.assignment.worker_id if task.assignment else None)
            if task.artifact_ids:
                rejected = run.artifacts[task.artifact_ids[-1]]
                rejected.status = "rejected"
                self._event(run, events, "artifact.rejected", artifact_id=rejected.id, reason=reason, failure_id=failure.id)
            decision = RecoveryDecision(failure_id=failure_id, action=action, reason=reason, actor_id=self.manager_id,
                context=f"Recovery from {failure.classification.value} on task {task.id}",
                options_considered=["RETRY", "REVISE", "REPLACE", "ESCALATE", "REPLAN"],
                consequences=[f"Task recovery action: {action}"], affected_ids=[task.id], evidence=[failure.evidence])
            run.recoveries.append(decision)
            run.decisions.append(decision)
            self._event(run, events, "recovery.decided", decision=decision.model_dump())
            return decision
        return self._mutate(run_id, operation)

    def request_approval(self, run_id: str, action: str, scope: dict, reason: str, *,
            category: str | None = None, target: str | None = None, risk: str = "material action",
            artifact_refs: list[str] | None = None, requested_capability: CapabilityProfile | None = None,
            required: bool = True, supersedes: str | None = None) -> ApprovalRequest:
        def operation(run, events):
            value, digest = _scope(scope)
            request = ApprovalRequest(run_id=run.id, category=category or action, action=action,
                scope_json=value, scope_digest=digest, target=target or str(scope.get("target") or scope.get("task_id") or "run"),
                rationale=reason, risk=risk, artifact_refs=artifact_refs or [],
                requested_capability=requested_capability, required=required)
            if supersedes is not None:
                prior = run.approvals.get(supersedes)
                if not prior or prior.status == ApprovalStatus.SUPERSEDED:
                    raise GateError("Approval is missing or already superseded")
                active = [task.id for task in run.tasks.values()
                    if task.status in {TaskStatus.DELEGATED, TaskStatus.RUNNING,
                        TaskStatus.SUBMITTED, TaskStatus.REVIEWING}
                    and any(gate.request_id == supersedes for gate in task.approval_gates)]
                if active:
                    raise GateError("Cannot supersede approval while bound work is active; fail and recover the task first")
                timestamp = now()
                run.approvals[supersedes] = prior.model_copy(update={"status": ApprovalStatus.SUPERSEDED,
                    "updated_at": timestamp, "superseded_at": timestamp, "replacement_id": request.id})
                self._event(run, events, "approval.superseded", approval_id=supersedes, replacement_id=request.id)
                for task in run.tasks.values():
                    for index, gate in enumerate(task.approval_gates):
                        if gate.request_id == supersedes:
                            replacement_gate = ApprovalGate(request_id=request.id, action=request.action,
                                scope_json=request.scope_json, scope_digest=request.scope_digest)
                            task.approval_gates[index] = replacement_gate
                            if task.status == TaskStatus.READY:
                                self._transition(run, events, task, TaskStatus.BLOCKED, "Replacement approval pending")
                            task.blocker = "Required approval pending"
                            self._event(run, events, "task.approval_gate_replaced", task_id=task.id,
                                prior_approval_id=supersedes, gate=replacement_gate.model_dump(mode="json"))
            run.approvals[request.id] = request
            self._event(run, events, "approval.required", request=request.model_dump(mode="json"))
            return request
        return self._mutate(run_id, operation)

    def recover_legacy_approval_gate(self, run_id: str, task_id: str, legacy_approval_id: str,
            approval_id: str, action: str, scope: dict):
        """Replace one unresolved schema-v1 bare approval ID with an exact typed gate."""
        def operation(run, events):
            task = run.tasks[task_id]
            if legacy_approval_id not in task.approval_ids or task.status not in {
                    TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.BLOCKED}:
                raise GateError("Task has no recoverable legacy approval gate in a safe state")
            request = run.approvals.get(approval_id)
            value, digest = _scope(scope)
            if (not request or request.status == ApprovalStatus.SUPERSEDED or
                    request.action != action or request.scope_json != value or
                    request.scope_digest != digest):
                raise GateError("Recovery gate must match the exact approval request")
            if any(gate.request_id == approval_id for gate in task.approval_gates):
                raise GateError("Approval gate already attached")
            gate = ApprovalGate(request_id=approval_id, action=action,
                scope_json=value, scope_digest=digest)
            task.approval_gates.append(gate)
            task.approval_ids.remove(legacy_approval_id)
            if task.approval_ids:
                task.blocker = ("Legacy approval gate requires explicit Manager re-gating: " +
                    ", ".join(task.approval_ids))
            elif request.status == ApprovalStatus.APPROVED:
                task.blocker = ("Capability prerequisites missing" if
                    task.capability == CapabilityProfile.DEVELOPER_SANDBOX and not task.workspace_id
                    else "Approval prerequisites satisfied")
            else:
                task.blocker = ("Required approval rejected" if request.status == ApprovalStatus.REJECTED
                    else "Required approval pending")
            self._event(run, events, "task.legacy_approval_gate_recovered", task_id=task_id,
                legacy_approval_id=legacy_approval_id, gate=gate.model_dump(mode="json"))
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def gate_task(self, run_id: str, task_id: str, approval_id: str, action: str, scope: dict):
        """Bind a task gate to an exact typed approval action and scope."""
        def operation(run, events):
            task = run.tasks[task_id]
            if task.status not in {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.BLOCKED} or task.attempts:
                raise GateError("Approval gates must be attached before delegation")
            request = run.approvals.get(approval_id)
            value, digest = _scope(scope)
            if (not request or request.status == ApprovalStatus.SUPERSEDED or
                    request.action != action or request.scope_digest != digest or request.scope_json != value):
                raise GateError("Task gate must match the exact approval request")
            gate = ApprovalGate(request_id=approval_id, action=action, scope_json=value, scope_digest=digest)
            if any(existing.request_id == approval_id for existing in task.approval_gates):
                raise GateError("Approval gate already attached")
            task.approval_gates.append(gate)
            if task.status == TaskStatus.READY and request.status != ApprovalStatus.APPROVED:
                self._transition(run, events, task, TaskStatus.BLOCKED, "Required approval pending")
                task.blocker = ("Required approval rejected" if request.status == ApprovalStatus.REJECTED
                    else "Required approval pending")
            self._event(run, events, "task.approval_gated", task_id=task_id, gate=gate.model_dump(mode="json"))
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def decide_approval(self, run_id: str, approval_id: str, approved: bool, human_id: str, reason: str):
        def operation(run, events):
            request = run.approvals.get(approval_id)
            if not request or request.status != ApprovalStatus.PENDING or approval_id in run.approval_decisions:
                raise GateError("Approval missing or already decided")
            status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            decision = ApprovalDecision(request_id=approval_id, approved=approved, human_id=human_id, reason=reason, status=status)
            run.approval_decisions[approval_id] = decision
            timestamp = now()
            run.approvals[approval_id] = request.model_copy(update={"status": status, "updated_at": timestamp, "decided_at": timestamp})
            self._event(run, events, "approval.granted" if approved else "approval.rejected", decision=decision.model_dump())
            for task in run.tasks.values():
                if any(g.request_id == approval_id for g in task.approval_gates):
                    if approved and task.status == TaskStatus.BLOCKED and task.blocker == "Required approval pending":
                        task.blocker = ("Capability prerequisites missing" if
                            task.capability == CapabilityProfile.DEVELOPER_SANDBOX and not task.workspace_id
                            else "Approval prerequisites satisfied")
                    elif not approved:
                        task.blocker = "Required approval rejected"
            self._refresh(run, events)
            return decision
        return self._mutate(run_id, operation)

    @staticmethod
    def _approved(run, approval_id, action, scope):
        request = run.approvals.get(approval_id)
        decision = run.approval_decisions.get(approval_id)
        value, digest = _scope(scope)
        if (not request or request.status != ApprovalStatus.APPROVED or not decision or not decision.approved or
                request.action != action or request.scope_digest != digest or request.scope_json != value):
            raise GateError("Exact scoped human approval required")

    def require_approval(self, run_id: str, approval_id: str, action: str, scope: dict):
        self._approved(self.get_run(run_id), approval_id, action, scope)

    def change_capability(self, run_id: str, task_id: str, capability: CapabilityProfile, approval_id: str, *, workspace_id: str | None = None):
        capability = CapabilityProfile(capability)
        def operation(run, events):
            task = run.tasks[task_id]
            if task.status not in {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.REVISION_REQUIRED, TaskStatus.BLOCKED}:
                raise GateError("Cannot change capabilities of active or terminal task")
            scope = {"task_id":task_id, "capability":capability.value, "workspace_id":workspace_id}
            self._approved(run, approval_id, "change_capability", scope)
            task.capability, task.workspace_id = capability, workspace_id
            self._event(run, events, "capability.escalated", **scope, approval_id=approval_id)
            if task.status == TaskStatus.READY and not self._ready(run, task):
                self._transition(run, events, task, TaskStatus.BLOCKED, "Capability prerequisites missing")
                task.blocker = "Capability prerequisites missing"
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def propose_replan(self, run_id: str, proposal: ReplanProposal) -> ReplanProposal:
        def operation(run, events):
            if proposal.base_revision != run.plan.revision or proposal.id in run.replans:
                raise GateError("Stale or duplicate replan")
            run.replans[proposal.id] = proposal.model_copy(deep=True)
            self._event(run, events, "plan.replan_proposed", proposal=proposal.model_dump(mode="json"))
            return proposal.model_copy(deep=True)
        return self._mutate(run_id, operation)

    def apply_replan(self, run_id: str, proposal_id: str):
        def operation(run, events):
            proposal = run.replans[proposal_id]
            if proposal.base_revision != run.plan.revision or run.plan.revision >= run.plan.max_replans:
                raise GateError("Stale proposal or replan budget exhausted")
            if proposal.requires_approval:
                self._approved(run, proposal.approval_id, "replan", {"proposal_id":proposal.id, "base_revision":proposal.base_revision})
            affected = set(proposal.reopen + proposal.remove + list(proposal.dependencies))
            if not affected.issubset(run.tasks):
                raise GateError("Unknown task in replan")
            # Invalidate transitive consumers, including explicit artifact dependencies.
            changed = True
            while changed:
                changed = False
                artifact_ids = {a for key in affected for a in run.tasks[key].artifact_ids}
                for key, task in run.tasks.items():
                    if key not in affected and set(task.packet.dependencies) & (affected | artifact_ids):
                        affected.add(key)
                        changed = True
            for key in affected:
                task = run.tasks[key]
                for artifact_id in task.artifact_ids:
                    run.artifacts[artifact_id].status = "superseded"
                    self._event(run, events, "artifact.superseded", artifact_id=artifact_id,
                        reason=proposal.trigger, proposal_id=proposal.id)
                    if artifact_id in run.accepted_artifacts:
                        run.accepted_artifacts.remove(artifact_id)
                task.status = TaskStatus.CANCELLED if key in proposal.remove else TaskStatus.PLANNED
                task.assignment = None
                task.result = None
                task.blocker = None
                self._event(run, events, "task.invalidated", task_id=key, reason=proposal.trigger)
            for key, deps in proposal.dependencies.items():
                run.tasks[key].packet.dependencies = list(deps)
            for source in proposal.add:
                if source.id in run.tasks or source.status != TaskStatus.PLANNED or source.attempts or source.assignment or source.artifact_ids:
                    raise GateError("Replan additions must be fresh unique tasks")
                run.tasks[source.id] = source.model_copy(deep=True)
            self._graph(run)
            run.plan.task_ids = [key for key,t in run.tasks.items() if t.status != TaskStatus.CANCELLED]
            run.plan.revision += 1
            run.plan.revision_history.append(proposal.model_copy(deep=True))
            self._event(run, events, "plan.replan_applied", proposal_id=proposal.id, revision=run.plan.revision, invalidated=sorted(affected))
            self._refresh(run, events)
        self._mutate(run_id, operation)

    def complete(self, run_id: str, final_result: str, *, criterion_evidence: dict[str, list[str]]) -> Run:
        def operation(run, events):
            active = [t for t in run.tasks.values() if t.status != TaskStatus.CANCELLED]
            if not active or any(t.status != TaskStatus.ACCEPTED for t in active) or run.unresolved_issues:
                raise GateError("Required work remains unresolved")
            if any(request.required and request.status == ApprovalStatus.PENDING for request in run.approvals.values()):
                raise GateError("Outstanding required approval gate")
            if set(criterion_evidence) != set(run.plan.completion_criteria) or any(not ids or not set(ids).issubset(run.accepted_artifacts) for ids in criterion_evidence.values()):
                raise GateError("Every completion criterion requires accepted artifact evidence")
            if not final_result.strip():
                raise GateError("Final result required")
            run.final_result, run.status, run.plan.status = final_result, "completed", "completed"
            self._event(run, events, "run.completed", criterion_evidence=criterion_evidence)
        self._mutate(run_id, operation)
        return self.get_run(run_id)
