import pytest
from walter.contracts import CapabilityRequestPayload, TaskPacket, WorkerResult
from walter.models import (ApprovalStatus, CapabilityProfile, CapabilityRequestStatus,
    FailureClass, ReplanProposal, TaskNode, TaskStatus)
from walter.orchestration import GateError, Orchestrator
from walter.store import SQLiteStore


def task(name="a", deps=(), **kwargs):
    return TaskNode(packet=TaskPacket(task_id=name, role="writer", objective="Write", deliverable="report", acceptance_criteria=["accurate"], stop_condition="deliver", dependencies=list(deps)), **kwargs)


@pytest.fixture
def kernel():
    store = SQLiteStore()
    core = Orchestrator(store)
    run = core.create_run("objective", ["accurate"])
    yield core, run.id
    store.close()


def candidate(core, rid, tid="a", worker="author", **kwargs):
    assignment = core.delegate(rid, tid, worker)
    core.start(rid, tid)
    return core.submit(rid, tid, assignment.id, worker,
        WorkerResult(task_id=tid, status="completed", summary="done", deliverable="inspectable report"), **kwargs)


def accepted(core, rid, tid="a"):
    artifact = candidate(core, rid, tid)
    core.review(rid, artifact.id, "reviewer", True, "Checked the report against sources")
    core.accept(rid, tid, "manager", "Criteria checked")
    return artifact


def test_dependency_requires_acceptance_and_completion_evidence(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(), task("b", ["a"])])
    with pytest.raises(GateError):
        core.start(rid, "a")
    with pytest.raises(GateError):
        core.delegate(rid, "b", "worker")
    artifact = candidate(core, rid)
    assert core.get_run(rid).tasks["b"].status == TaskStatus.PLANNED
    with pytest.raises(GateError):
        core.accept(rid, "a", "manager", "Worker says done")
    with pytest.raises(GateError):
        core.review(rid, artifact.id, "author", True, "self approval")
    core.review(rid, artifact.id, "reviewer", True, "Independent inspection")
    with pytest.raises(GateError):
        core.accept(rid, "a", "author", "self approval")
    core.accept(rid, "a", "manager", "Inspection passed")
    assert core.get_run(rid).tasks["b"].status == TaskStatus.READY
    b = accepted(core, rid, "b")
    with pytest.raises(GateError):
        core.complete(rid, "done", criterion_evidence={"accurate": ["missing"]})
    core.complete(rid, "done", criterion_evidence={"accurate": [b.id]})
    with pytest.raises(GateError):
        core.start(rid, "a")


def test_inputs_graph_and_atomic_failure(kernel):
    core, rid = kernel
    a = task()
    a.packet.required_inputs = ["source"]
    core.add_tasks(rid, [a])
    with pytest.raises(GateError):
        core.delegate(rid, "a", "worker")
    core.register_input(rid, "source", "trusted://source")
    assert core.get_run(rid).tasks["a"].status == TaskStatus.READY
    before = core.get_run(rid)
    with pytest.raises(GateError):
        core.add_tasks(rid, [task("b", ["c"]), task("c", ["b"])])
    assert core.get_run(rid) == before
    with pytest.raises(GateError):
        core.register_input(rid, "source", "changed")


def test_validation_failure_cannot_self_certify(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(required_checks=["tests"], review_required=False)])
    artifact = candidate(core, rid)
    with pytest.raises(GateError):
        core.validate(rid, artifact.id, "tests", True, "self claim", "author")
    core.validate(rid, artifact.id, "tests", False, "exit 1", "executor")
    with pytest.raises(GateError):
        core.accept(rid, "a", "manager", "ignore failed tests")
    core.validate(rid, artifact.id, "tests", True, "exit 0 after environment correction", "executor")
    core.accept(rid, "a", "manager", "Tests pass")


def test_revision_lineage_limits_and_failure_routing(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(max_revisions=1)])
    a = candidate(core, rid)
    core.review(rid, a.id, "reviewer", False, "Incorrect result")
    failure = core.fail(rid, "a", FailureClass.BAD_OUTPUT, "Wrong answer")
    decision = core.recover(rid, failure.id, "Correct cited issue")
    assert decision.action == "REVISE"
    with pytest.raises(GateError):
        core.recover(rid, failure.id, "repeat")
    b = candidate(core, rid)
    assert b.predecessor_id == a.id and b.version == 2
    core.review(rid, b.id, "reviewer", False, "Still wrong")
    failure = core.fail(rid, "a", FailureClass.BAD_OUTPUT, "Same issue")
    assert core.recover(rid, failure.id, "Reassess worker fit").action == "REPLACE"
    with pytest.raises(GateError):
        core.delegate(rid, "a", "new-worker")


@pytest.mark.parametrize("classification,action", [(FailureClass.PROVIDER_FAILURE,"RETRY"), (FailureClass.TASK_AMBIGUITY,"REPLAN"), (FailureClass.TOOL_FAILURE,"ESCALATE"), (FailureClass.REPEATED_BAD_OUTPUT,"REPLACE")])
def test_failure_classes(kernel, classification, action):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    failure = core.fail(rid, "a", classification, "Runtime evidence")
    assert core.recover(rid, failure.id, "Specific corrective action").action == action


def test_replan_invalidates_accepted_transitive_consumers(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(), task("b", ["a"]), task("c", ["b"])])
    arts = [accepted(core, rid, tid) for tid in ["a", "b", "c"]]
    proposal = ReplanProposal(base_revision=0, trigger="Source invalid", evidence=["Contradiction"], reopen=["a"])
    core.propose_replan(rid, proposal)
    core.apply_replan(rid, proposal.id)
    run = core.get_run(rid)
    assert run.accepted_artifacts == []
    assert all(run.artifacts[a.id].status == "superseded" for a in arts)
    assert run.tasks["a"].status == TaskStatus.READY
    assert run.tasks["b"].status == TaskStatus.PLANNED
    assert run.tasks["c"].status == TaskStatus.PLANNED
    assert run.plan.revision == 1
    with pytest.raises(GateError):
        core.apply_replan(rid, proposal.id)
    with pytest.raises(GateError):
        core.review(rid, arts[0].id, "reviewer", True, "stale")


def test_replan_is_atomic_and_bounded(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    bad = ReplanProposal(base_revision=0, trigger="bad graph", evidence=["test"], dependencies={"a":["missing"]})
    core.propose_replan(rid, bad)
    before = core.get_run(rid)
    with pytest.raises(GateError):
        core.apply_replan(rid, bad.id)
    assert core.get_run(rid) == before
    for revision in range(3):
        proposal = ReplanProposal(base_revision=revision, trigger="reopen", evidence=["new facts"], reopen=["a"])
        core.propose_replan(rid, proposal)
        core.apply_replan(rid, proposal.id)
    proposal = ReplanProposal(base_revision=3, trigger="again", evidence=["new facts"], reopen=["a"])
    core.propose_replan(rid, proposal)
    with pytest.raises(GateError):
        core.apply_replan(rid, proposal.id)


def test_approvals_exact_scope_immutable_and_completion_gate(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    artifact = accepted(core, rid)
    scope = {"commit":"abc", "artifact_id":artifact.id}
    request = core.request_approval(rid, "promote", scope, "Candidate promotion")
    with pytest.raises(GateError):
        core.complete(rid, "done", criterion_evidence={"accurate":[artifact.id]})
    core.decide_approval(rid, request.id, True, "human", "Reviewed exact candidate")
    core.require_approval(rid, request.id, "promote", scope)
    with pytest.raises(GateError):
        core.require_approval(rid, request.id, "promote", {**scope,"commit":"def"})
    with pytest.raises(GateError):
        core.decide_approval(rid, request.id, False, "human", "rewrite")


def test_capability_approval_and_fingerprint(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(required_checks=["compile"])])
    scope = {"task_id":"a", "capability":"developer_sandbox", "workspace_id":"workspace"}
    request = core.request_approval(rid, "change_capability", scope, "Requires editing")
    with pytest.raises(GateError):
        core.change_capability(rid, "a", CapabilityProfile.DEVELOPER_SANDBOX, request.id, workspace_id="workspace")
    core.decide_approval(rid, request.id, True, "operator", "Bounded workspace")
    core.change_capability(rid, "a", CapabilityProfile.DEVELOPER_SANDBOX, request.id, workspace_id="workspace")
    artifact = candidate(core, rid, workspace_fingerprint="tree-abc")
    with pytest.raises(GateError):
        core.review(rid, artifact.id, "reviewer", True, "checked", workspace_fingerprint="tree-def")
    core.validate(rid, artifact.id, "compile", True, "compile succeeded", "executor",
        workspace_fingerprint="tree-abc")
    core.review(rid, artifact.id, "reviewer", True, "checked", workspace_fingerprint="tree-abc")
    with pytest.raises(GateError):
        core.accept(rid, "a", "manager", "pass", workspace_fingerprint="tree-def")
    core.accept(rid, "a", "manager", "pass", workspace_fingerprint="tree-abc")


def test_developer_sandbox_requires_executable_check_on_initial_plan(kernel):
    core, rid = kernel
    with pytest.raises(GateError, match="compile, unittest, or pytest"):
        core.add_tasks(rid, [task(capability=CapabilityProfile.DEVELOPER_SANDBOX,
            workspace_id="workspace", required_checks=["result_schema"])])
    assert core.get_run(rid).tasks == {}


def test_replan_rejects_schema_only_developer_addition_atomically(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    proposal = ReplanProposal(base_revision=0, trigger="Need implementation", evidence=["Gap"],
        add=[task("developer", capability=CapabilityProfile.DEVELOPER_SANDBOX,
            workspace_id="workspace", required_checks=["result_schema"])])
    core.propose_replan(rid, proposal)
    before = core.get_run(rid)
    with pytest.raises(GateError, match="compile, unittest, or pytest"):
        core.apply_replan(rid, proposal.id)
    assert core.get_run(rid) == before


def test_approved_capability_change_cannot_bypass_executable_check(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(required_checks=["result_schema"])])
    scope = {"task_id": "a", "capability": "developer_sandbox", "workspace_id": "workspace"}
    approval = core.request_approval(rid, "change_capability", scope,
        "Approved developer escalation")
    core.decide_approval(rid, approval.id, True, "human", "Approved exact scope")
    before = core.get_run(rid)
    with pytest.raises(GateError, match="compile, unittest, or pytest"):
        core.change_capability(rid, "a", CapabilityProfile.DEVELOPER_SANDBOX,
            approval.id, workspace_id="workspace")
    assert core.get_run(rid) == before


def test_resume_no_silent_rerun(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    assert core.reload(rid).tasks["a"].status == TaskStatus.RUNNING
    run = core.resume(rid)
    assert run.tasks["a"].status == TaskStatus.FAILED
    assert run.failures[-1].classification == FailureClass.TIMEOUT
    with pytest.raises(GateError):
        core.delegate(rid, "a", "author")
    core.recover(rid, run.failures[-1].id, "Interrupted assignment inspected; safe to retry")
    core.delegate(rid, "a", "author")


def test_task_approval_gate_is_typed_and_exact(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    expected_scope = {"task_id": "a", "operation": "publish report"}
    request = core.request_approval(rid, "publish", expected_scope, "Publication is consequential")
    unrelated = core.request_approval(rid, "publish", {"task_id": "b"}, "Different target", required=False)
    with pytest.raises(GateError, match="exact"):
        core.gate_task(rid, "a", unrelated.id, "publish", expected_scope)
    core.gate_task(rid, "a", request.id, "publish", expected_scope)
    assert core.get_run(rid).tasks["a"].status == TaskStatus.BLOCKED
    core.decide_approval(rid, unrelated.id, True, "human", "Approved another target")
    assert core.get_run(rid).tasks["a"].status == TaskStatus.BLOCKED
    core.decide_approval(rid, request.id, True, "human", "Approved exact action")
    assert core.get_run(rid).tasks["a"].status == TaskStatus.READY


def test_approved_exact_gate_does_not_regress_ready_task(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    scope = {"task_id": "a", "operation": "bounded action"}
    request = core.request_approval(rid, "execute", scope, "Exact bounded action")
    core.decide_approval(rid, request.id, True, "human", "Approved")
    core.gate_task(rid, "a", request.id, "execute", scope)
    assert core.get_run(rid).tasks["a"].status == TaskStatus.READY


def test_active_task_approval_cannot_be_superseded_until_failure_recovery(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    old_scope = {"task_id": "a", "operation": "publish v1"}
    old = core.request_approval(rid, "publish", old_scope, "Initial proposal")
    core.gate_task(rid, "a", old.id, "publish", old_scope)
    core.decide_approval(rid, old.id, True, "human", "Approved exact v1 scope")
    core.delegate(rid, "a", "author")
    core.start(rid, "a")

    with pytest.raises(GateError, match="bound work is active"):
        core.request_approval(rid, "publish", {"task_id": "a", "operation": "publish v2"},
            "Changed scope", supersedes=old.id)
    run = core.get_run(rid)
    assert run.approvals[old.id].status == ApprovalStatus.APPROVED
    assert run.tasks["a"].approval_gates[0].request_id == old.id

    failure = core.fail(rid, "a", FailureClass.PROVIDER_FAILURE, "Stop work before changing scope")
    core.recover(rid, failure.id, "Assignment stopped and inspected")
    replacement = core.request_approval(rid, "publish", {"task_id": "a", "operation": "publish v2"},
        "Changed scope", supersedes=old.id)
    run = core.get_run(rid)
    assert run.tasks["a"].status == TaskStatus.BLOCKED
    assert run.tasks["a"].approval_gates[0].request_id == replacement.id
    with pytest.raises(GateError):
        core.submit(rid, "a", run.tasks["a"].assignment.id, "author",
            WorkerResult(task_id="a", status="completed",
            summary="stale", deliverable="work performed under v1 scope"))


def test_old_assignment_cannot_submit_after_recovery_reapproval_and_redelegation(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    old_scope = {"task_id": "a", "operation": "publish v1"}
    old_approval = core.request_approval(rid, "publish", old_scope, "Initial scope")
    core.gate_task(rid, "a", old_approval.id, "publish", old_scope)
    core.decide_approval(rid, old_approval.id, True, "human", "Approved v1")
    old_assignment = core.delegate(rid, "a", "old-worker")
    core.start(rid, "a")
    failure = core.fail(rid, "a", FailureClass.PROVIDER_FAILURE, "Stop old assignment")
    core.recover(rid, failure.id, "Inspected before retry")

    new_scope = {"task_id": "a", "operation": "publish v2"}
    new_approval = core.request_approval(rid, "publish", new_scope, "Replacement scope",
        supersedes=old_approval.id)
    core.decide_approval(rid, new_approval.id, True, "human", "Approved v2")
    new_assignment = core.delegate(rid, "a", "new-worker")
    core.start(rid, "a")
    stale = WorkerResult(task_id="a", status="completed", summary="late",
        deliverable="late work produced under v1")
    with pytest.raises(GateError, match="current worker assignment"):
        core.submit(rid, "a", old_assignment.id, "old-worker", stale)
    current = WorkerResult(task_id="a", status="completed", summary="current",
        deliverable="work produced under v2")
    artifact = core.submit(rid, "a", new_assignment.id, "new-worker", current)
    assert artifact.worker_id == "new-worker"
    assert core.get_run(rid).tasks["a"].status == TaskStatus.SUBMITTED


def test_old_assignment_cannot_fail_redelegated_work(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    old_assignment = core.delegate(rid, "a", "old-worker")
    core.start(rid, "a")
    old_failure = core.fail_assignment(rid, "a", old_assignment.id, "old-worker",
        FailureClass.PROVIDER_FAILURE, "Old execution interrupted")
    core.recover(rid, old_failure.id, "Retry after inspecting interruption")
    new_assignment = core.delegate(rid, "a", "new-worker")
    core.start(rid, "a")

    before = core.get_run(rid)
    events_before = core.store.events(rid)
    with pytest.raises(GateError, match="current worker assignment"):
        core.fail_assignment(rid, "a", old_assignment.id, "old-worker",
            FailureClass.TOOL_FAILURE, "Late stale callback")
    assert core.get_run(rid) == before
    assert core.store.events(rid) == events_before
    assert core.get_run(rid).tasks["a"].status == TaskStatus.RUNNING

    failure = core.fail_assignment(rid, "a", new_assignment.id, "new-worker",
        FailureClass.TOOL_FAILURE, "Current worker failed")
    run = core.get_run(rid)
    assert run.tasks["a"].status == TaskStatus.FAILED
    assert run.failures[-1] == failure
    assert [event.kind for event in core.store.events(rid)][-3:] == [
        "task.failed", "failure.classified", "assignment.failed"]


def test_capability_request_preserves_partial_work_and_requires_manager_escalation(tmp_path):
    path = tmp_path / "capability-request.db"
    store = SQLiteStore(path)
    core = Orchestrator(store)
    rid = core.create_run("objective", ["accurate"]).id
    core.add_tasks(rid, [task(), task("downstream", ["a"])])
    assignment = core.delegate(rid, "a", "worker")
    core.start(rid, "a")
    result = WorkerResult(task_id="a", status="blocked", summary="Repository access needed",
        deliverable="Partial analysis with reusable findings", evidence=["Inspected supplied context"],
        blocker="Cannot inspect repository", capability_request=CapabilityRequestPayload(
            requested_capability="repo_reader", reason="Need to inspect implementation files",
            risk="Read-only access may expose repository content"))

    before = core.get_run(rid)
    with pytest.raises(GateError, match="current active assignment"):
        core.record_capability_request(rid, "a", assignment.id, "forged-worker", result)
    assert core.get_run(rid) == before
    request = core.record_capability_request(rid, "a", assignment.id, "worker", result)
    run = core.reload(rid)
    assert run.capability_requests[request.id] == request
    assert request.status == CapabilityRequestStatus.PENDING
    assert run.tasks["a"].result.deliverable == "Partial analysis with reusable findings"
    assert run.tasks["a"].result.evidence == ["Inspected supplied context"]
    assert run.tasks["a"].artifact_ids == []
    assert run.tasks["downstream"].status == TaskStatus.PLANNED

    failure = core.fail_assignment(rid, "a", assignment.id, "worker",
        FailureClass.CAPABILITY_UNAVAILABLE, "Requested repository access is unavailable")
    assert core.recover(rid, failure.id, "Evaluate bounded capability escalation").action == "ESCALATE"
    assert core.get_run(rid).tasks["a"].status == TaskStatus.BLOCKED
    scope = {"task_id": "a", "capability": "repo_reader", "workspace_id": "repo-workspace"}
    approval = core.request_approval(rid, "change_capability", scope,
        "Grant requested read-only repository access", requested_capability=CapabilityProfile.REPO_READER)
    with pytest.raises(GateError, match="workspace binding"):
        core.link_capability_approval(rid, request.id, approval.id)
    core.link_capability_approval(rid, request.id, approval.id, workspace_id="repo-workspace")
    with pytest.raises(GateError, match="has not been granted"):
        core.approve_capability_request(rid, request.id)
    core.decide_approval(rid, approval.id, True, "human", "Approved bounded read-only access")
    store.close()

    store = SQLiteStore(path)
    core = Orchestrator(store)
    applied = core.apply_capability_escalation(rid, request.id)
    assert applied.status == CapabilityRequestStatus.ESCALATED
    run = core.reload(rid)
    assert run.capability_requests[request.id].status == CapabilityRequestStatus.ESCALATED
    assert run.tasks["a"].capability == CapabilityProfile.REPO_READER
    assert run.tasks["a"].workspace_id == "repo-workspace"
    assert run.tasks["a"].status == TaskStatus.READY
    assert run.tasks["a"].result.deliverable == "Partial analysis with reusable findings"
    assert run.tasks["downstream"].status == TaskStatus.PLANNED
    version, events = run.version, list(core.store.events(rid))
    assert core.apply_capability_escalation(rid, request.id) == applied
    assert core.get_run(rid).version == version
    assert core.store.events(rid) == events
    store.close()

    reloaded = SQLiteStore(path)
    assert reloaded.load(rid).capability_requests[request.id].status == CapabilityRequestStatus.ESCALATED
    reloaded.close()


@pytest.mark.parametrize("status,classification", [
    ("blocked", FailureClass.MISSING_EVIDENCE),
    ("needs_revision", FailureClass.BAD_OUTPUT),
])
def test_noncompleted_worker_result_is_preserved_without_candidate_or_dependency_unlock(
        kernel, status, classification):
    core, rid = kernel
    core.add_tasks(rid, [task(), task("downstream", ["a"])])
    assignment = core.delegate(rid, "a", "worker")
    core.start(rid, "a")
    result = WorkerResult(task_id="a", status=status, summary="Partial result",
        deliverable="Useful partial work", evidence=["partial evidence"], blocker="More work required")
    core.record_provisional_result(rid, "a", assignment.id, "worker", result)
    failure = core.fail_assignment(rid, "a", assignment.id, "worker", classification,
        "Trusted classification of provisional result")
    run = core.get_run(rid)
    assert run.tasks["a"].result == result
    assert run.tasks["a"].artifact_ids == []
    assert run.tasks["downstream"].status == TaskStatus.PLANNED
    assert run.failures[-1] == failure
    assert core.recover(rid, failure.id, "Preserve partial work for explicit revision").action == "REVISE"
    run = core.get_run(rid)
    assert run.tasks["a"].status == TaskStatus.REVISION_REQUIRED
    assert run.tasks["a"].result.deliverable == "Useful partial work"
    assert run.tasks["downstream"].status == TaskStatus.PLANNED


def test_manager_can_deny_capability_request_without_grant(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    assignment = core.delegate(rid, "a", "worker")
    core.start(rid, "a")
    result = WorkerResult(task_id="a", status="blocked", summary="Requests write access",
        deliverable="Partial work", capability_request=CapabilityRequestPayload(
            requested_capability="developer_sandbox", reason="Need to edit files",
            risk="Write access changes candidate files"))
    request = core.record_capability_request(rid, "a", assignment.id, "worker", result)
    core.deny_capability_request(rid, request.id, "Task must remain read-only")
    run = core.get_run(rid)
    assert run.capability_requests[request.id].status == CapabilityRequestStatus.DENIED
    assert run.tasks["a"].capability == CapabilityProfile.MODEL_ONLY
    assert core.store.events(rid)[-1].kind == "capability.denied"


def test_new_task_gate_rejects_superseded_request(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    scope = {"task_id": "a", "operation": "publish"}
    obsolete = core.request_approval(rid, "publish", scope, "Obsolete request")
    core.request_approval(rid, "publish", scope, "Current request", supersedes=obsolete.id)
    with pytest.raises(GateError, match="exact approval request"):
        core.gate_task(rid, "a", obsolete.id, "publish", scope)
    assert core.get_run(rid).tasks["a"].approval_gates == []


@pytest.mark.parametrize("old_approved", [False, True])
def test_decided_task_approval_can_be_audited_and_atomically_replaced(kernel, old_approved):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    old_scope = {"task_id": "a", "operation": "publish v1"}
    old = core.request_approval(rid, "publish", old_scope, "Initial proposal")
    core.gate_task(rid, "a", old.id, "publish", old_scope)
    core.decide_approval(rid, old.id, old_approved, "human", "Initial decision")
    expected = TaskStatus.READY if old_approved else TaskStatus.BLOCKED
    assert core.get_run(rid).tasks["a"].status == expected

    revised_scope = {"task_id": "a", "operation": "publish v2"}
    revised = core.request_approval(rid, "publish_revised", revised_scope,
        "Materially revised proposal", supersedes=old.id)
    run = core.get_run(rid)
    assert run.approvals[old.id].status == ApprovalStatus.SUPERSEDED
    assert old.id in run.approval_decisions
    assert run.tasks["a"].status == TaskStatus.BLOCKED
    assert run.tasks["a"].approval_gates[0].request_id == revised.id
    assert run.tasks["a"].approval_gates[0].action == "publish_revised"
    with pytest.raises(GateError, match="Exact scoped"):
        core.require_approval(rid, old.id, "publish", old_scope)

    core.decide_approval(rid, revised.id, True, "human", "Approved revised proposal")
    assert core.get_run(rid).tasks["a"].status == TaskStatus.READY


def test_approval_lifecycle_supersedes_without_erasing_audit(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    artifact = accepted(core, rid)
    first = core.request_approval(rid, "promote", {"commit": "old"}, "Old candidate")
    replacement = core.request_approval(rid, "promote", {"commit": "new"}, "Changed candidate", supersedes=first.id)
    run = core.get_run(rid)
    assert run.approvals[first.id].status == ApprovalStatus.SUPERSEDED
    assert run.approvals[first.id].replacement_id == replacement.id
    assert run.approvals[replacement.id].status == ApprovalStatus.PENDING
    with pytest.raises(GateError, match="Outstanding"):
        core.complete(rid, "done", criterion_evidence={"accurate": [artifact.id]})
    core.decide_approval(rid, replacement.id, False, "human", "Do not promote")
    assert core.get_run(rid).approvals[replacement.id].status == ApprovalStatus.REJECTED
    core.complete(rid, "work complete without promotion", criterion_evidence={"accurate": [artifact.id]})


def test_configured_manager_authority_cannot_be_spoofed_or_supply_evidence():
    store = SQLiteStore()
    core = Orchestrator(store, manager_id="trusted-manager")
    rid = core.create_run("objective", ["accurate"]).id
    core.add_tasks(rid, [task(required_checks=["tests"])])
    with pytest.raises(GateError):
        core.delegate(rid, "a", "trusted-manager")
    artifact = candidate(core, rid)
    with pytest.raises(GateError):
        core.validate(rid, artifact.id, "tests", True, "exit 0", "trusted-manager")
    with pytest.raises(GateError):
        core.review(rid, artifact.id, "trusted-manager", True, "review")
    core.validate(rid, artifact.id, "tests", True, "exit 0", "executor")
    core.review(rid, artifact.id, "reviewer", True, "independent review")
    with pytest.raises(GateError, match="configured Manager"):
        core.accept(rid, "a", "spoofed-manager", "accept")
    decision = core.accept(rid, "a", reason="Trusted acceptance")
    assert decision.actor_id == "trusted-manager"
    store.close()


def test_workspace_can_resolve_blocked_capability_escalation(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(required_checks=["compile"])])
    scope = {"task_id": "a", "capability": "developer_sandbox", "workspace_id": None}
    request = core.request_approval(rid, "change_capability", scope, "Needs a developer sandbox")
    core.decide_approval(rid, request.id, True, "operator", "Approved bounded capability")
    core.change_capability(rid, "a", CapabilityProfile.DEVELOPER_SANDBOX, request.id)
    assert core.get_run(rid).tasks["a"].status == TaskStatus.BLOCKED
    core.bind_workspace(rid, "a", "workspace-a")
    assert core.get_run(rid).tasks["a"].status == TaskStatus.READY


def test_recovered_developer_task_workspace_replacement_is_exact_audited_and_durable(tmp_path):
    path = tmp_path / "workspace-replacement.db"
    store = SQLiteStore(path)
    core = Orchestrator(store)
    rid = core.create_run("objective", ["accurate"]).id
    core.add_tasks(rid, [task(capability=CapabilityProfile.DEVELOPER_SANDBOX,
        workspace_id="workspace-v1", required_checks=["compile"])])

    with pytest.raises(GateError, match="after recovery"):
        core.replace_workspace(rid, "a", "workspace-v1", "workspace-v2", "Initial task is not a retry")
    core.delegate(rid, "a", "developer")
    core.start(rid, "a")
    with pytest.raises(GateError, match="after recovery"):
        core.replace_workspace(rid, "a", "workspace-v1", "workspace-v2", "Still active")

    failure = core.fail(rid, "a", FailureClass.PROVIDER_FAILURE, "Worker environment interrupted")
    core.recover(rid, failure.id, "Retry in a clean Manager-created sandbox")
    with pytest.raises(GateError, match="does not match"):
        core.replace_workspace(rid, "a", "wrong-workspace", "workspace-v2", "Wrong expected identity")
    core.replace_workspace(rid, "a", "workspace-v1", "workspace-v2", "Fresh sandbox for bounded retry")
    run = core.get_run(rid)
    assert run.tasks["a"].workspace_id == "workspace-v2"
    event = core.store.events(rid)[-1]
    assert event.kind == "workspace.replaced"
    assert event.data == {"task_id": "a", "old_workspace_id": "workspace-v1",
        "new_workspace_id": "workspace-v2", "reason": "Fresh sandbox for bounded retry"}
    store.close()

    reloaded_store = SQLiteStore(path)
    reloaded = Orchestrator(reloaded_store).reload(rid)
    assert reloaded.tasks["a"].workspace_id == "workspace-v2"
    Orchestrator(reloaded_store).delegate(rid, "a", "replacement-developer")
    assert Orchestrator(reloaded_store).get_run(rid).tasks["a"].assignment.workspace_id == "workspace-v2"
    reloaded_store.close()


def test_workspace_replacement_denies_candidate_and_terminal_states(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(capability=CapabilityProfile.DEVELOPER_SANDBOX,
        workspace_id="workspace-v1", required_checks=["compile"])])
    artifact = candidate(core, rid, workspace_fingerprint="tree-v1")
    with pytest.raises(GateError, match="after recovery"):
        core.replace_workspace(rid, "a", "workspace-v1", "workspace-v2", "Candidate still under review")
    core.review(rid, artifact.id, "reviewer", True, "Reviewed candidate",
        workspace_fingerprint="tree-v1")
    core.validate(rid, artifact.id, "compile", True, "compile succeeded", "executor",
        workspace_fingerprint="tree-v1")
    core.accept(rid, "a", "manager", "Accepted", workspace_fingerprint="tree-v1")
    with pytest.raises(GateError, match="after recovery"):
        core.replace_workspace(rid, "a", "workspace-v1", "workspace-v2", "Task is terminal")


def test_lifecycle_events_cover_assignment_artifact_retry_and_replacement(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    artifact = candidate(core, rid)
    failure = core.fail(rid, "a", FailureClass.PROVIDER_FAILURE, "provider unavailable")
    core.recover(rid, failure.id, "Retry after transient outage")
    kinds = [event.kind for event in core.store.events(rid)]
    assert {"assignment.created", "assignment.started", "assignment.completed", "assignment.failed",
            "artifact.created", "artifact.submitted", "artifact.rejected",
            "retry.scheduled"}.issubset(kinds)
    assert artifact.id in core.get_run(rid).artifacts


def test_escalate_unsupported_capability_blocks_task(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    failure = core.fail(rid, "a", FailureClass.UNSUPPORTED_CAPABILITY, "Requested capability is not offered")
    decision = core.recover(rid, failure.id, "Escalate to Manager for capability decision")
    run = core.get_run(rid)
    assert decision.action == "ESCALATE"
    assert run.tasks["a"].status == TaskStatus.BLOCKED
    assert run.tasks["a"].blocker == "Unsupported capability requires Manager escalation"


def test_escalate_tool_failure_blocks_task(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    failure = core.fail(rid, "a", FailureClass.TOOL_FAILURE, "Sandbox executor crashed")
    decision = core.recover(rid, failure.id, "Escalate tooling repair to Manager")
    run = core.get_run(rid)
    assert decision.action == "ESCALATE"
    assert run.tasks["a"].status == TaskStatus.BLOCKED
    assert run.tasks["a"].blocker == "Tool failure requires Manager escalation"


def test_replan_recovery_blocks_task_until_manager_replans(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    failure = core.fail(rid, "a", FailureClass.TASK_AMBIGUITY, "Objective admits two contradictory readings")
    decision = core.recover(rid, failure.id, "Route ambiguity to explicit replan")
    run = core.get_run(rid)
    assert decision.action == "REPLAN"
    assert run.tasks["a"].status == TaskStatus.BLOCKED
    assert run.tasks["a"].blocker == "Manager replan required"
    proposal = ReplanProposal(base_revision=0, trigger="Ambiguity resolved", evidence=["Operator clarified scope"], reopen=["a"])
    core.propose_replan(rid, proposal)
    core.apply_replan(rid, proposal.id)
    run = core.get_run(rid)
    assert run.tasks["a"].status == TaskStatus.READY
    assert run.tasks["a"].blocker is None


def test_recovery_retry_clears_blocker(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task()])
    core.delegate(rid, "a", "author")
    core.start(rid, "a")
    failure = core.fail(rid, "a", FailureClass.PROVIDER_FAILURE, "Provider timeout")
    assert core.get_run(rid).tasks["a"].blocker == "Provider timeout"
    decision = core.recover(rid, failure.id, "Bounded retry after transient provider failure")
    run = core.get_run(rid)
    assert decision.action == "RETRY"
    assert run.tasks["a"].status == TaskStatus.READY
    assert run.tasks["a"].blocker is None


def test_recovery_revise_and_replace_record_blockers(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task(max_revisions=1)])
    candidate(core, rid)
    failure = core.fail(rid, "a", FailureClass.BAD_OUTPUT, "Wrong answer")
    decision = core.recover(rid, failure.id, "Targeted revision")
    run = core.get_run(rid)
    assert decision.action == "REVISE"
    assert run.tasks["a"].status == TaskStatus.REVISION_REQUIRED
    assert run.tasks["a"].blocker == "Wrong answer"
    candidate(core, rid)
    failure = core.fail(rid, "a", FailureClass.BAD_OUTPUT, "Same issue")
    decision = core.recover(rid, failure.id, "Revision limit reached; reassess worker fit")
    run = core.get_run(rid)
    assert decision.action == "REPLACE"
    assert run.tasks["a"].status == TaskStatus.REPLACED
    assert run.tasks["a"].blocker == "Worker replacement required"
