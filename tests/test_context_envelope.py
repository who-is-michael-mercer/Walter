import asyncio
import json

import pytest

pytest.importorskip("agents")

from walter.adapter import (CONTEXT_ENVELOPE_MAX_BYTES, DurableController,
                            ReviewResult)
from walter.contracts import TaskPacket, WorkerResult
from walter.models import FailureClass, TaskNode
from walter.orchestration import Orchestrator
from walter.store import SQLiteStore


def packet(task_id, **updates):
    values = {
        "task_id": task_id,
        "role": "bounded fixture specialist",
        "objective": f"Produce {task_id}",
        "deliverable": "One inspectable result",
        "acceptance_criteria": ["result is present"],
        "stop_condition": "result submitted or a concrete blocker is reported",
    }
    values.update(updates)
    return TaskPacket(**values)


def completed(task_id, content):
    return WorkerResult(
        task_id=task_id, status="completed", summary="complete", deliverable=content
    )


def test_downstream_and_reviewer_receive_only_declared_resolved_inputs(monkeypatch):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("context routing", ["downstream result accepted"])
    core.register_input(run.id, "declared-ref", "immutable://source/42")
    core.register_input(run.id, "unrelated-secret", "SECRET-MUST-NOT-LEAK")
    core.add_tasks(run.id, [
        TaskNode(packet=packet("upstream"), required_checks=["result_schema"]),
        TaskNode(packet=packet("unrelated"), required_checks=["result_schema"]),
        TaskNode(packet=packet(
            "downstream", dependencies=["upstream"], required_inputs=["declared-ref"]
        ), required_checks=["result_schema"]),
    ])
    controller = DurableController(core, run.id)
    calls = []

    async def invoke(**kwargs):
        calls.append((kwargs["output_type"], json.loads(kwargs["input"])))
        if kwargs["output_type"] is ReviewResult:
            return ReviewResult(passed=True, evidence=["criterion checked"], reason="passes")
        active = [task.id for task in controller.inspect().tasks.values()
                  if task.status == "RUNNING"]
        task_id = active[0]
        # Adapter overwrites this untrusted task ID with the assigned task.
        content = ("ACCEPTED-UPSTREAM-CONTENT" if task_id == "upstream"
                   else "unused")
        if task_id == "downstream":
            return WorkerResult(
                task_id=task_id, status="completed", summary="DOWNSTREAM-SUMMARY",
                deliverable=content, evidence=["DOWNSTREAM-EVIDENCE"],
                sources=[{
                    "title": "Declared source", "url": "https://example.invalid/source",
                    "note": "DOWNSTREAM-SOURCE-NOTE",
                }],
                assumptions=["DOWNSTREAM-ASSUMPTION"],
                uncertainties=["DOWNSTREAM-UNCERTAINTY"],
                acceptance_check=[{
                    "criterion": "result is present", "passed": True,
                    "note": "DOWNSTREAM-CHECK-NOTE",
                }],
            )
        return completed(task_id, content)

    monkeypatch.setattr(controller, "_invoke", invoke)

    upstream = asyncio.run(controller.delegate("upstream"))
    controller.validate("upstream")
    asyncio.run(controller.review("upstream"))
    core.accept(run.id, "upstream", reason="fixture accepted")

    unrelated = asyncio.run(controller.delegate("unrelated"))
    failed = core.fail(run.id, "unrelated", FailureClass.BAD_OUTPUT,
                       "UNRELATED-REJECTED-EVIDENCE")
    core.recover(run.id, failed.id, "revise unrelated work")
    assert controller.inspect().artifacts[unrelated.id].status == "rejected"

    calls.clear()
    downstream = asyncio.run(controller.delegate("downstream"))
    worker_envelope = calls[-1][1]
    by_id = {item["declared_id"]: item for item in worker_envelope["declared_inputs"]}
    assert list(by_id) == ["declared-ref", "upstream"]
    assert by_id["declared-ref"] == {
        "declared_as": ["required_input"],
        "declared_id": "declared-ref",
        "kind": "registered_input_reference",
        "reference": "immutable://source/42",
    }
    assert by_id["upstream"]["kind"] == "accepted_artifact"
    assert by_id["upstream"]["artifact_id"] == upstream.id
    assert by_id["upstream"]["content"] == "ACCEPTED-UPSTREAM-CONTENT"
    assert by_id["upstream"]["content_digest"]
    serialized = json.dumps(worker_envelope, sort_keys=True)
    assert "SECRET-MUST-NOT-LEAK" not in serialized
    assert "UNRELATED-REJECTED-EVIDENCE" not in serialized
    assert unrelated.id not in serialized

    controller.validate("downstream")
    calls.clear()
    asyncio.run(controller.review("downstream"))
    reviewer_envelope = calls[-1][1]
    assert reviewer_envelope["declared_inputs"] == worker_envelope["declared_inputs"]
    assert reviewer_envelope["candidate"]["artifact_id"] == downstream.id
    assert reviewer_envelope["candidate"]["content_digest"] == downstream.content_digest
    assert reviewer_envelope["candidate"]["label"].startswith("provisional_")
    current_result = reviewer_envelope["current_worker_result"]
    task = controller.inspect().tasks["downstream"]
    assert current_result["label"] == "provisional_current_worker_result"
    assert current_result["task_id"] == "downstream"
    assert current_result["artifact_id"] == downstream.id
    assert current_result["content_digest"] == downstream.content_digest
    assert current_result["worker_id"] == downstream.worker_id
    assert current_result["assignment_id"] == task.assignment.id
    assert current_result["summary"] == "DOWNSTREAM-SUMMARY"
    assert current_result["evidence"] == ["DOWNSTREAM-EVIDENCE"]
    assert current_result["sources"][0]["note"] == "DOWNSTREAM-SOURCE-NOTE"
    assert current_result["assumptions"] == ["DOWNSTREAM-ASSUMPTION"]
    assert current_result["uncertainties"] == ["DOWNSTREAM-UNCERTAINTY"]
    assert current_result["acceptance_check"][0]["note"] == "DOWNSTREAM-CHECK-NOTE"
    assert "deliverable" not in current_result
    assert reviewer_envelope["validation_evidence"][0]["artifact_id"] == downstream.id
    assert reviewer_envelope["validation_evidence"][0]["label"].startswith("provisional_")
    reviewer_serialized = json.dumps(reviewer_envelope, sort_keys=True)
    assert "SECRET-MUST-NOT-LEAK" not in reviewer_serialized
    assert "UNRELATED-REJECTED-EVIDENCE" not in reviewer_serialized
    assert unrelated.id not in reviewer_serialized


def test_second_revision_receives_bound_partial_and_corrective_evidence(monkeypatch):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("revision context", ["corrected result accepted"])
    core.add_tasks(run.id, [TaskNode(
        packet=packet("revise"), required_checks=["result_schema"]
    )])
    controller = DurableController(core, run.id)
    captured = []

    async def first(**kwargs):
        return completed("revise", "USEFUL-PARTIAL-CANDIDATE")

    monkeypatch.setattr(controller, "_invoke", first)
    artifact = asyncio.run(controller.delegate("revise"))
    controller.validate("revise")

    async def rejecting_review(**kwargs):
        return ReviewResult(
            passed=False, evidence=["CORRECTIVE-REVIEW-EVIDENCE"],
            reason="criterion needs correction",
        )

    monkeypatch.setattr(controller, "_invoke", rejecting_review)
    asyncio.run(controller.review("revise"))
    failed = core.fail(run.id, "revise", FailureClass.BAD_OUTPUT,
                       "CORRECTIVE-FAILURE-EVIDENCE")
    recovery = core.recover(run.id, failed.id, "Apply the reviewer correction")

    async def second(**kwargs):
        captured.append(json.loads(kwargs["input"]))
        return completed("revise", "corrected candidate")

    monkeypatch.setattr(controller, "_invoke", second)
    asyncio.run(controller.delegate("revise"))
    revision = captured[0]["revision_context"]
    assert revision["label"] == "provisional_corrective_context"
    assert revision["prior_result"]["result"]["deliverable"] == "USEFUL-PARTIAL-CANDIDATE"
    assert revision["prior_result"]["assignment_id"]
    assert revision["prior_candidate"]["artifact_id"] == artifact.id
    assert revision["prior_candidate"]["status"] == "rejected"
    assert revision["validation_evidence"][0]["artifact_id"] == artifact.id
    assert revision["review_evidence"][0]["artifact_id"] == artifact.id
    assert "CORRECTIVE-REVIEW-EVIDENCE" in revision["review_evidence"][0]["evidence"]
    assert revision["failure"]["failure_id"] == failed.id
    assert revision["failure"]["evidence"] == "CORRECTIVE-FAILURE-EVIDENCE"
    assert revision["recovery"]["recovery_id"] == recovery.id
    assert revision["recovery"]["failure_id"] == failed.id
    assert revision["recovery"]["reason"] == "Apply the reviewer correction"


@pytest.mark.parametrize(
    ("context", "malformed", "message"),
    [
        ("x" * CONTEXT_ENVELOPE_MAX_BYTES, False, "exceeds"),
        ("ordinary persisted context", True, "valid JSON/UTF-8"),
    ],
)
def test_invalid_context_fails_before_worker_call_without_state_corruption(
        monkeypatch, context, malformed, message):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("bounded envelope", ["result accepted"])
    core.add_tasks(run.id, [TaskNode(
        packet=packet("task", context=context), required_checks=["result_schema"]
    )])
    controller = DurableController(core, run.id)
    invoked = False

    if malformed:
        original = TaskPacket.model_dump

        def invalid_dump(self, *args, **kwargs):
            value = original(self, *args, **kwargs)
            value["context"] = object()
            return value

        monkeypatch.setattr(TaskPacket, "model_dump", invalid_dump)

    async def should_not_run(**kwargs):
        nonlocal invoked
        invoked = True
        return completed("task", "unexpected")

    monkeypatch.setattr(controller, "_invoke", should_not_run)
    before = controller.inspect()
    with pytest.raises(ValueError, match=message):
        asyncio.run(controller.delegate("task"))
    after = controller.inspect()
    assert not invoked
    assert after.version == before.version
    assert after.tasks["task"].status == "READY"
    assert after.tasks["task"].attempts == 0
    assert after.tasks["task"].assignment is None
    assert after.failures == []
