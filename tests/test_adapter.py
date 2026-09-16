import asyncio
import json
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("agents")

from walter.adapter import (DurableController, INITIAL_COMPLETION_CRITERION,
                            ReviewResult)
from walter.contracts import TaskPacket, WorkerResult
from walter.models import CapabilityProfile, FailureClass, TaskNode
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
