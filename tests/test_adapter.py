import asyncio
import json
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("agents")

from walter.adapter import (DurableController, INITIAL_COMPLETION_CRITERION,
                            ReviewResult)
from walter.contracts import TaskPacket, WorkerResult
from walter.models import CapabilityProfile, CapabilityRequestStatus, FailureClass, TaskNode
from walter.orchestration import Orchestrator
from walter.sandbox import WorkspaceManager
from walter.store import SQLiteStore
from walter.adapter import workspace_tools


def packet(task_id="task"):
    return TaskPacket(
        task_id=task_id,
        role="fixture specialist",
        objective="Produce a bounded fixture result",
        deliverable="One inspectable result",
        acceptance_criteria=["result is present"],
        stop_condition="result submitted",
    )


def controller_for(task, tmp_path=None):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("fixture", ["accepted fixture"])
    core.add_tasks(run.id, [task])
    return DurableController(core, run.id)


def test_manager_tool_surface_has_no_trust_forging_tools():
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))
    tools = {item.name: item for item in controller.tools()}
    assert set(tools) == {
        "inspect_run", "set_completion_criteria", "plan_tasks", "delegate_task",
        "validate_task", "review_task", "accept_task", "recover_task", "replan_tasks",
        "apply_replan",
        "request_capability_change", "apply_capability_change",
        "request_approval", "request_candidate_approval", "authorize_candidate_action",
        "finish_run",
    }
    assert "passed" not in tools["validate_task"].params_json_schema["properties"]
    assert "evidence" not in tools["validate_task"].params_json_schema["properties"]
    assert "approved" not in tools["request_approval"].params_json_schema["properties"]
    assert "decide_approval" not in tools
    assert "submit_artifact" not in tools


def test_placeholder_criteria_block_planning_and_delegation():
    core = Orchestrator(SQLiteStore())
    run = core.create_run("broad goal", [INITIAL_COMPLETION_CRITERION])
    controller = DurableController(core, run.id)
    with pytest.raises(ValueError, match="completion criteria"):
        asyncio.run(controller.delegate("missing"))
    controller.set_criteria(["A persisted artifact passes the declared result schema check"])
    assert controller.inspect().plan.completion_criteria == [
        "A persisted artifact passes the declared result schema check"
    ]


def test_workspace_tool_surface_matches_read_and_write_grants():
    class Manager:
        pass

    read_only = {item.name for item in workspace_tools(Manager(), "grant", "reader", writable=False)}
    writable = {item.name for item in workspace_tools(Manager(), "grant", "writer", writable=True)}
    assert read_only == {"read_file", "list_files", "inspect_diff", "workspace_status"}
    assert writable == read_only | {"write_file", "delete_file", "run_check"}


def test_model_only_delegation_persists_provisional_submission(monkeypatch):
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))
    observed = {}

    async def fake_invoke(**kwargs):
        observed.update(kwargs)
        return WorkerResult(task_id="untrusted", status="completed", summary="done",
                            deliverable="fixture output")

    monkeypatch.setattr(controller, "_invoke", fake_invoke)
    artifact = asyncio.run(controller.delegate("task"))
    run = controller.inspect()
    assert artifact.worker_id.startswith("worker-")
    assert observed["tools"] == []
    assert run.tasks["task"].status == "SUBMITTED"
    assert not run.accepted_artifacts


def test_researcher_capability_receives_only_runtime_search_grant(monkeypatch):
    task = TaskNode(packet=packet(), capability=CapabilityProfile.RESEARCHER,
                    required_checks=["result_schema"])
    controller = controller_for(task)
    marker = object()
    observed = {}
    monkeypatch.setattr("walter.adapter.runtime._tools_for", lambda policy: [marker] if policy == "web_search" else [])

    async def fake_invoke(**kwargs):
        observed.update(kwargs)
        return WorkerResult(task_id="task", status="completed", summary="done",
                            deliverable="researched output")

    monkeypatch.setattr(controller, "_invoke", fake_invoke)
    asyncio.run(controller.delegate("task"))
    assert observed["tools"] == [marker]


def test_review_records_fresh_identity_and_cannot_accept_by_itself(monkeypatch):
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))

    async def author(**kwargs):
        return WorkerResult(task_id="task", status="completed", summary="done",
                            deliverable="fixture output")

    monkeypatch.setattr(controller, "_invoke", author)
    asyncio.run(controller.delegate("task"))
    controller.validate("task")

    async def reviewer(**kwargs):
        return ReviewResult(passed=True, evidence=["checked criterion"], reason="passes")

    monkeypatch.setattr(controller, "_invoke", reviewer)
    asyncio.run(controller.review("task"))
    run = controller.inspect()
    artifact = run.artifacts[run.tasks["task"].artifact_ids[-1]]
    assert artifact.reviews[-1].reviewer_id != artifact.worker_id
    assert run.tasks["task"].status == "REVIEWING"
    assert not run.accepted_artifacts


def test_developer_revision_gets_fresh_workspace_and_cleans_old_candidate(tmp_path, monkeypatch):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "fixture",
    ], check=True)
    core = Orchestrator(SQLiteStore())
    run = core.create_run("developer revision", ["A revised candidate is submitted"])
    core.add_tasks(run.id, [TaskNode(
        packet=packet(), capability=CapabilityProfile.DEVELOPER_SANDBOX,
        required_checks=["compile"],
    )])
    workspaces = WorkspaceManager(repository)
    controller = DurableController(core, run.id, workspaces)

    async def candidate(**kwargs):
        return WorkerResult(task_id="task", status="completed", summary="candidate",
                            deliverable="bounded candidate")

    monkeypatch.setattr(controller, "_invoke", candidate)
    asyncio.run(controller.delegate("task"))
    first = controller.inspect().tasks["task"].workspace_id
    first_root = Path(workspaces.inspect_grant(first).root)
    failure = core.fail(run.id, "task", FailureClass.BAD_OUTPUT, "revision required")
    core.recover(run.id, failure.id, "commission a corrected candidate")

    asyncio.run(controller.delegate("task"))
    current = controller.inspect()
    second = current.tasks["task"].workspace_id
    assert second != first
    assert not first_root.exists()
    assert current.tasks["task"].status == "SUBMITTED"
    assert any(event.kind == "workspace.replaced" for event in core.store.events(run.id))


@pytest.mark.parametrize("stale_outcome", ["completion", "error"])
def test_stale_worker_cannot_fail_new_running_assignment(monkeypatch, stale_outcome):
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))
    core = controller.core

    async def scenario():
        first_started = asyncio.Event()
        second_started = asyncio.Event()
        release_first = asyncio.Event()
        release_second = asyncio.Event()
        calls = 0

        async def invoke(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                first_started.set()
                await release_first.wait()
                if stale_outcome == "error":
                    raise RuntimeError("old worker failed late")
                return WorkerResult(task_id="task", status="completed", summary="stale",
                                    deliverable="stale completion")
            second_started.set()
            await release_second.wait()
            return WorkerResult(task_id="task", status="completed", summary="current",
                                deliverable="current completion")

        monkeypatch.setattr(controller, "_invoke", invoke)
        first_call = asyncio.create_task(controller.delegate("task"))
        await first_started.wait()
        first_assignment = controller.inspect().tasks["task"].assignment
        failure = core.fail_assignment(
            controller.run_id, "task", first_assignment.id, first_assignment.worker_id,
            FailureClass.PROVIDER_FAILURE, "manager observed interrupted provider call",
        )
        core.recover(controller.run_id, failure.id, "retry with a fresh worker")

        second_call = asyncio.create_task(controller.delegate("task"))
        await second_started.wait()
        second_assignment = controller.inspect().tasks["task"].assignment
        assert second_assignment.id != first_assignment.id
        release_first.set()
        with pytest.raises(Exception):
            await first_call
        current = controller.inspect().tasks["task"]
        assert current.status == "RUNNING"
        assert current.assignment.id == second_assignment.id

        release_second.set()
        artifact = await second_call
        assert artifact.worker_id == second_assignment.worker_id
        assert controller.inspect().tasks["task"].status == "SUBMITTED"

    asyncio.run(scenario())


def test_material_replan_waits_for_exact_approval_and_rejection_cannot_apply():
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))
    proposal, approval = controller.propose_replan(
        trigger="remove obsolete work", evidence=["objective changed"], add=[],
        remove=["task"], reopen=[], dependencies={}, risks=["task is cancelled"],
    )
    assert proposal.requires_approval and approval is not None
    assert controller.inspect().plan.revision == 0
    with pytest.raises(ValueError, match="approval"):
        controller.apply_replan(proposal.id)
    controller.core.decide_approval(controller.run_id, approval.id, False,
                                    "human", "do not alter the plan")
    with pytest.raises(ValueError, match="approval"):
        controller.apply_replan(proposal.id)


def test_exact_approved_material_replan_applies_and_stale_one_fails():
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))
    stale, stale_approval = controller.propose_replan(
        trigger="candidate removal", evidence=["new constraint"], add=[],
        remove=["task"], reopen=[], dependencies={}, risks=[],
    )
    additive_packet = packet("additive")
    additive, approval = controller.propose_replan(
        trigger="add independent evidence", evidence=["coverage gap"], add=[additive_packet],
        remove=[], reopen=[], dependencies={}, risks=[],
    )
    assert approval is not None
    assert controller.inspect().plan.revision == 0
    controller.core.decide_approval(controller.run_id, approval.id, True,
                                    "human", "approve exact additive proposal")
    controller.apply_replan(additive.id)
    assert controller.inspect().plan.revision == 1
    controller.core.decide_approval(controller.run_id, stale_approval.id, True,
                                    "human", "approve original revision")
    with pytest.raises(ValueError, match="Stale proposal"):
        controller.apply_replan(stale.id)

    current, current_approval = controller.propose_replan(
        trigger="remove obsolete original", evidence=["superseded by additive"], add=[],
        remove=["task"], reopen=[], dependencies={}, risks=[],
    )
    controller.core.decide_approval(controller.run_id, current_approval.id, True,
                                    "human", "approve exact current proposal")
    controller.apply_replan(current.id)
    run = controller.inspect()
    assert run.plan.revision == 2
    assert run.tasks["task"].status == "CANCELLED"


@pytest.mark.parametrize("status", ["blocked", "needs_revision"])
def test_provisional_worker_result_is_preserved_and_routed_without_submission(monkeypatch, status):
    controller = controller_for(TaskNode(packet=packet(), required_checks=["result_schema"]))

    async def provisional(**kwargs):
        return WorkerResult(task_id="task", status=status, summary="partial result",
                            deliverable="useful partial evidence", blocker="criterion unresolved")

    monkeypatch.setattr(controller, "_invoke", provisional)
    result = asyncio.run(controller.delegate("task"))
    run = controller.inspect()
    assert result.status == status
    assert run.tasks["task"].status == "REVISION_REQUIRED"
    assert run.tasks["task"].result.deliverable == "useful partial evidence"
    assert not run.tasks["task"].artifact_ids
    assert run.failures[-1].classification in {FailureClass.BAD_OUTPUT, FailureClass.MISSING_EVIDENCE}


def _controller_with_capability_request(monkeypatch, repository, *, checks=None,
                                        requested="developer_sandbox"):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("capability escalation", ["A bounded candidate is produced"])
    if checks is None:
        checks = ["compile"] if requested == "developer_sandbox" else ["result_schema"]
    core.add_tasks(run.id, [TaskNode(packet=packet(), required_checks=checks)])
    controller = DurableController(core, run.id, WorkspaceManager(repository))
    observed = {}

    async def blocked(**kwargs):
        observed["tools"] = kwargs["tools"]
        return WorkerResult(
            task_id="task", status="blocked", summary="repository write access required",
            deliverable="analysis completed before capability boundary",
            blocker="developer sandbox required",
            capability_request={
                "requested_capability": requested,
                "reason": "Implement the accepted bounded change",
                "risk": "Candidate source can be modified only in isolation",
            },
        )

    monkeypatch.setattr(controller, "_invoke", blocked)
    asyncio.run(controller.delegate("task"))
    request = next(iter(controller.inspect().capability_requests.values()))
    return controller, request, observed


def test_capability_escalation_pending_and_denied_never_grants_tools(tmp_path, monkeypatch):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    controller, request, observed = _controller_with_capability_request(monkeypatch, repository)
    assert observed["tools"] == []
    run = controller.inspect()
    assert run.tasks["task"].status == "BLOCKED"
    assert run.tasks["task"].capability == CapabilityProfile.MODEL_ONLY

    linked, approval = controller.request_capability_change(request.id, "Human review required")
    workspace_id = json.loads(approval.scope_json)["workspace_id"]
    assert linked.approval_id == approval.id
    assert controller.inspect().tasks["task"].workspace_id is None
    with pytest.raises(ValueError, match="not been granted"):
        controller.apply_capability_change(request.id)
    controller.core.decide_approval(controller.run_id, approval.id, False,
                                    "human", "deny repository write access")
    with pytest.raises(ValueError, match="denied"):
        controller.apply_capability_change(request.id)
    run = controller.inspect()
    assert run.capability_requests[request.id].status == CapabilityRequestStatus.DENIED
    assert run.tasks["task"].capability == CapabilityProfile.MODEL_ONLY
    with pytest.raises(Exception):
        controller.workspaces.inspect_grant(workspace_id)


def test_developer_escalation_without_executable_check_is_denied_before_allocation(tmp_path, monkeypatch):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    controller, request, _ = _controller_with_capability_request(
        monkeypatch, repository, checks=["result_schema"]
    )
    with pytest.raises(ValueError, match="requires compile"):
        controller.request_capability_change(request.id, "unsafe escalation")
    run = controller.inspect()
    assert run.capability_requests[request.id].status == CapabilityRequestStatus.DENIED
    assert run.approvals == {}
    assert run.tasks["task"].workspace_id is None
    sandboxes = repository / ".local" / "sandboxes"
    assert not list(sandboxes.glob("candidate-*"))


def test_exact_approved_capability_request_applies_persisted_profile(tmp_path, monkeypatch):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    controller, request, _ = _controller_with_capability_request(monkeypatch, repository)
    _, approval = controller.request_capability_change(request.id, "Review exact sandbox grant")
    controller.core.decide_approval(controller.run_id, approval.id, True,
                                    "human", "approve isolated candidate workspace")
    run = controller.apply_capability_change(request.id)
    scope = json.loads(approval.scope_json)
    assert run.capability_requests[request.id].status == CapabilityRequestStatus.ESCALATED
    assert run.tasks["task"].capability == CapabilityProfile.DEVELOPER_SANDBOX
    assert run.tasks["task"].workspace_id == scope["workspace_id"]
    assert run.tasks["task"].status == "READY"

    version = run.version
    reloaded = DurableController(
        Orchestrator(controller.core.store), controller.run_id, WorkspaceManager(repository)
    )
    reloaded_run = reloaded.apply_capability_change(request.id)
    assert reloaded_run.version == version

    async def completed(**kwargs):
        return WorkerResult(task_id="task", status="completed", summary="implemented",
                            deliverable="approved workspace candidate")

    monkeypatch.setattr(reloaded, "_invoke", completed)
    artifact = asyncio.run(reloaded.delegate("task"))
    after = reloaded.inspect()
    assert after.tasks["task"].workspace_id == scope["workspace_id"]
    assert artifact.workspace_fingerprint == reloaded.workspaces.fingerprint(scope["workspace_id"])
    replacements = [event for event in reloaded.core.store.events(reloaded.run_id)
                    if event.kind == "workspace.replaced"]
    assert replacements == []


def test_repo_reader_escalation_reuses_exact_workspace_with_read_only_tools(tmp_path, monkeypatch):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    controller, request, _ = _controller_with_capability_request(
        monkeypatch, repository, requested="repo_reader"
    )
    _, approval = controller.request_capability_change(request.id, "Approve bounded repository reads")
    scope = json.loads(approval.scope_json)
    assert scope["workspace_id"]
    controller.core.decide_approval(controller.run_id, approval.id, True,
                                    "human", "approve read-only repository access")
    run = controller.apply_capability_change(request.id)
    assert run.tasks["task"].capability == CapabilityProfile.REPO_READER
    assert run.tasks["task"].workspace_id == scope["workspace_id"]
    observed = {}

    async def completed(**kwargs):
        observed["tools"] = {tool.name for tool in kwargs["tools"]}
        return WorkerResult(task_id="task", status="completed", summary="inspected",
                            deliverable="repository inspection")

    monkeypatch.setattr(controller, "_invoke", completed)
    asyncio.run(controller.delegate("task"))
    assert observed["tools"] == {"read_file", "list_files", "inspect_diff", "workspace_status"}
    assert controller.inspect().tasks["task"].workspace_id == scope["workspace_id"]
