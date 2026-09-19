import pytest

from walter.contracts import TaskPacket, WorkerResult
from walter.models import FailureClass, ReplanProposal, TaskNode, TaskStatus
from walter.orchestration import GateError, Orchestrator
from walter.store import SQLiteStore


def task(**kwargs):
    return TaskNode(packet=TaskPacket(
        task_id="task",
        role="worker",
        objective="Produce a result",
        deliverable="Inspectable result",
        acceptance_criteria=["Result is accurate"],
        stop_condition="Return the result",
    ), **kwargs)


def failed(core, run_id, classification):
    assignment = core.delegate(run_id, "task", "worker")
    core.start(run_id, "task")
    return core.fail_assignment(
        run_id, "task", assignment.id, assignment.worker_id,
        classification, f"{classification.value} evidence",
    )


def assert_next_operation(core, run_id, status):
    if status in {TaskStatus.READY, TaskStatus.REVISION_REQUIRED}:
        core.delegate(run_id, "task", "next-worker")
        assert core.get_run(run_id).tasks["task"].status == TaskStatus.DELEGATED
        return
    proposal = ReplanProposal(
        base_revision=core.get_run(run_id).plan.revision,
        trigger="resolve recovery postcondition",
        evidence=["manager supplied a corrected plan"],
        reopen=["task"],
    )
    core.propose_replan(run_id, proposal)
    core.apply_replan(run_id, proposal.id)
    assert core.get_run(run_id).tasks["task"].status == TaskStatus.READY


@pytest.mark.parametrize(("classification", "action", "status", "blocker"), [
    (FailureClass.BAD_OUTPUT, "REVISE", TaskStatus.REVISION_REQUIRED, "BAD_OUTPUT evidence"),
    (FailureClass.MISSING_EVIDENCE, "REVISE", TaskStatus.REVISION_REQUIRED, "MISSING_EVIDENCE evidence"),
    (FailureClass.CONSTRAINT_VIOLATION, "REPLACE", TaskStatus.REPLACED, "Worker replacement required"),
    (FailureClass.TASK_AMBIGUITY, "REPLAN", TaskStatus.BLOCKED, "Manager replan required"),
    (FailureClass.DEPENDENCY_FAILURE, "REPLAN", TaskStatus.BLOCKED, "Manager replan required"),
    (FailureClass.TOOL_FAILURE, "ESCALATE", TaskStatus.BLOCKED, "Tool failure requires Manager escalation"),
    (FailureClass.PROVIDER_FAILURE, "RETRY", TaskStatus.READY, None),
    (FailureClass.TIMEOUT, "RETRY", TaskStatus.READY, None),
    (FailureClass.CAPABILITY_UNAVAILABLE, "ESCALATE", TaskStatus.BLOCKED, "Capability escalation pending"),
    (FailureClass.UNSUPPORTED_CAPABILITY, "ESCALATE", TaskStatus.BLOCKED, "Unsupported capability requires Manager escalation"),
    (FailureClass.REPEATED_BAD_OUTPUT, "REPLACE", TaskStatus.REPLACED, "Worker replacement required"),
])
def test_every_failure_class_has_an_explicit_recovery_postcondition(
        classification, action, status, blocker):
    store = SQLiteStore()
    core = Orchestrator(store)
    run = core.create_run("recover", ["result accepted"])
    core.add_tasks(run.id, [task()])
    failure = failed(core, run.id, classification)

    decision = core.recover(run.id, failure.id, "bounded recovery")
    current = core.get_run(run.id)

    assert decision.action == action
    assert current.tasks["task"].status == status
    assert current.tasks["task"].blocker == blocker
    assert current.tasks["task"].status != TaskStatus.FAILED
    with pytest.raises(GateError, match="already recovered"):
        core.recover(run.id, failure.id, "duplicate recovery")
    assert_next_operation(core, run.id, status)
    store.close()


@pytest.mark.parametrize(("classification", "node", "action", "status", "blocker"), [
    (FailureClass.PROVIDER_FAILURE, task(max_attempts=1), "REPLAN", TaskStatus.BLOCKED,
     "Manager replan required"),
    (FailureClass.TIMEOUT, task(max_attempts=1), "REPLAN", TaskStatus.BLOCKED,
     "Manager replan required"),
    (FailureClass.BAD_OUTPUT, task(max_attempts=1), "REPLAN", TaskStatus.BLOCKED,
     "Manager replan required"),
    (FailureClass.MISSING_EVIDENCE, task(max_attempts=1), "REPLAN", TaskStatus.BLOCKED,
     "Manager replan required"),
    (FailureClass.BAD_OUTPUT, task(max_attempts=3, max_revisions=0), "REPLACE",
     TaskStatus.REPLACED, "Worker replacement required"),
])
def test_exhaustion_has_an_explicit_nonfailed_postcondition(
        classification, node, action, status, blocker):
    store = SQLiteStore()
    core = Orchestrator(store)
    run = core.create_run("recover", ["result accepted"])
    core.add_tasks(run.id, [node])
    failure = failed(core, run.id, classification)

    decision = core.recover(run.id, failure.id, "bounded exhaustion")
    current = core.get_run(run.id)

    assert decision.action == action
    assert current.tasks["task"].status == status
    assert current.tasks["task"].blocker == blocker
    assert current.tasks["task"].status != TaskStatus.FAILED
    assert_next_operation(core, run.id, status)
    store.close()


def test_recovery_still_rejects_the_preserved_candidate():
    store = SQLiteStore()
    core = Orchestrator(store)
    run = core.create_run("recover", ["result accepted"])
    core.add_tasks(run.id, [task()])
    assignment = core.delegate(run.id, "task", "worker")
    core.start(run.id, "task")
    artifact = core.submit(run.id, "task", assignment.id, assignment.worker_id,
        WorkerResult(task_id="task", status="completed", summary="done",
                     deliverable="candidate"))
    failure = core.fail(run.id, "task", FailureClass.BAD_OUTPUT, "review found a defect")

    core.recover(run.id, failure.id, "revise the candidate")

    current = core.get_run(run.id)
    assert current.tasks["task"].status == TaskStatus.REVISION_REQUIRED
    assert current.artifacts[artifact.id].status == "rejected"
    store.close()
