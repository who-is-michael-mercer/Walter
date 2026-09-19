import pytest

from walter.contracts import TaskPacket, WorkerResult
from walter.models import Event, ReplanProposal, TaskNode, TaskStatus
from walter.orchestration import GateError, Orchestrator
from walter.store import SQLiteStore


def task(name, *, inputs=(), dependencies=()):
    return TaskNode(packet=TaskPacket(task_id=name, role="writer", objective="Write report",
        deliverable="report", acceptance_criteria=["accurate"], stop_condition="deliver",
        required_inputs=list(inputs), dependencies=list(dependencies)))


@pytest.fixture
def kernel():
    store = SQLiteStore()
    core = Orchestrator(store)
    run = core.create_run("objective", ["accurate"], max_replans=10)
    yield core, run.id
    store.close()


def submit(core, rid, name):
    assignment = core.delegate(rid, name, "author")
    core.start(rid, name)
    return core.submit(rid, name, assignment.id, "author", WorkerResult(
        task_id=name, status="completed", summary="done", deliverable="Checked report"))


def accept(core, rid, name):
    artifact = submit(core, rid, name)
    core.review(rid, artifact.id, "reviewer", True, "Checked sources")
    core.accept(rid, name, reason="Criteria checked")
    return artifact


def replan(core, rid, **changes):
    proposal = ReplanProposal(base_revision=core.get_run(rid).plan.revision,
        trigger="Source changed", evidence=["New evidence"], **changes)
    core.propose_replan(rid, proposal)
    core.apply_replan(rid, proposal.id)


@pytest.mark.parametrize("operation", ["reopen", "remove"])
@pytest.mark.parametrize("downstream_status", ["accepted", "submitted", "running"])
def test_required_artifact_replan_invalidates_transitive_work(kernel, operation, downstream_status):
    core, rid = kernel
    core.add_tasks(rid, [task("a")])
    a = accept(core, rid, "a")
    replan(core, rid, add=[task("b", inputs=[a.id]), task("c", dependencies=["b"])])
    b = accept(core, rid, "b")
    assert b.input_artifact_ids == [a.id]
    c = None
    if downstream_status == "accepted":
        c = accept(core, rid, "c")
    elif downstream_status == "submitted":
        c = submit(core, rid, "c")
        core.start_review(rid, c.id, "reviewer")
    else:
        assignment = core.delegate(rid, "c", "author")
        core.start(rid, "c")

    replan(core, rid, **{operation: ["a"]})
    run = core.get_run(rid)
    assert run.tasks["a"].status == (TaskStatus.READY if operation == "reopen" else TaskStatus.CANCELLED)
    assert run.tasks["b"].status == run.tasks["c"].status == TaskStatus.PLANNED
    assert run.tasks["b"].packet.required_inputs == [a.id]
    assert run.tasks["c"].assignment is None
    assert not run.reviews_in_flight
    assert not run.accepted_artifacts
    for artifact in [a, b] + ([c] if c else []):
        assert run.artifacts[artifact.id].status == "superseded"
    with pytest.raises(GateError):
        core.complete(rid, "done", criterion_evidence={"accurate": [b.id]})
    with pytest.raises(GateError):
        core.delegate(rid, "b", "author")
    if downstream_status == "running":
        with pytest.raises(GateError, match="assignment"):
            core.submit(rid, "c", assignment.id, "author", WorkerResult(
                task_id="c", status="completed", summary="late", deliverable="Late report"))
    if operation == "reopen":
        replacement = accept(core, rid, "a")
        assert replacement.id != a.id
        assert core.get_run(rid).tasks["b"].status == TaskStatus.PLANNED
        with pytest.raises(GateError):
            core.delegate(rid, "b", "author")


def test_required_artifact_edges_chain_transitively(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task("a")])
    a = accept(core, rid, "a")
    replan(core, rid, add=[task("b", inputs=[a.id])])
    b = accept(core, rid, "b")
    replan(core, rid, add=[task("c", inputs=[b.id])])
    c = accept(core, rid, "c")
    assert c.input_artifact_ids == [b.id]
    replan(core, rid, reopen=["a"])
    run = core.get_run(rid)
    assert all(run.artifacts[artifact.id].status == "superseded" for artifact in [a, b, c])
    assert run.tasks["c"].status == TaskStatus.PLANNED


def test_registered_input_still_unblocks_and_completes(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task("a", inputs=["source"])])
    assert core.get_run(rid).tasks["a"].status == TaskStatus.PLANNED
    core.register_input(rid, "source", "trusted://source")
    a = accept(core, rid, "a")
    assert a.input_artifact_ids == []
    assert core.complete(rid, "done", criterion_evidence={"accurate": [a.id]}).status == "completed"


@pytest.mark.parametrize("gate", ["accept", "complete"])
def test_missing_legacy_provenance_fails_closed(kernel, gate):
    core, rid = kernel
    core.add_tasks(rid, [task("a")])
    a = accept(core, rid, "a")
    replan(core, rid, add=[task("b", inputs=[a.id])])
    b = accept(core, rid, "b") if gate == "complete" else submit(core, rid, "b")
    if gate == "accept":
        core.review(rid, b.id, "reviewer", True, "Checked sources")
    # Simulate the persisted artifact produced before required-input lineage was recorded.
    run = core.get_run(rid)
    run.artifacts[b.id].input_artifact_ids = []
    core.store.save(run, [Event(run_id=rid, kind="test.legacy_provenance_fixture")], run.version)
    before = core.get_run(rid)
    with pytest.raises(GateError, match="provenance"):
        if gate == "accept":
            core.accept(rid, "b", reason="Criteria checked")
        else:
            core.complete(rid, "done", criterion_evidence={"accurate": [b.id]})
    assert core.get_run(rid) == before


def test_replan_artifact_producer_cycle_is_rejected_atomically(kernel):
    core, rid = kernel
    core.add_tasks(rid, [task("a")])
    a = accept(core, rid, "a")
    replan(core, rid, add=[task("b", inputs=[a.id])])
    b = accept(core, rid, "b")
    proposal = ReplanProposal(base_revision=core.get_run(rid).plan.revision,
        trigger="Invalid cyclic revision", evidence=["Test"], dependencies={"a": [b.id]})
    core.propose_replan(rid, proposal)
    before = core.get_run(rid)
    with pytest.raises(GateError, match="cycle"):
        core.apply_replan(rid, proposal.id)
    assert core.get_run(rid) == before
