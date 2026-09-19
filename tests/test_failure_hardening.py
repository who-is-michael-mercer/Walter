import asyncio

import pytest

pytest.importorskip("agents")

from walter.adapter import AdapterExecutionError, DurableController, SpecialistOutputError
from walter.contracts import TaskPacket, WorkerResult
from walter.models import FailureClass, TaskNode
from walter.orchestration import GateError, Orchestrator
from walter.store import SQLiteStore


SECRET = "SECRET_TOKEN=request-body-private"


def _task(*, max_review_attempts=3):
    return TaskNode(
        packet=TaskPacket(
            task_id="task",
            role="fixture specialist",
            objective="Produce a fixture",
            deliverable="One result",
            acceptance_criteria=["result exists"],
            stop_condition="result submitted",
        ),
        required_checks=["result_schema"],
        max_review_attempts=max_review_attempts,
    )


def _controller(*, max_review_attempts=3):
    core = Orchestrator(SQLiteStore())
    run = core.create_run("fixture", ["accepted fixture"])
    core.add_tasks(run.id, [_task(max_review_attempts=max_review_attempts)])
    return DurableController(core, run.id)


def _persisted(controller):
    return (
        controller.inspect().model_dump_json()
        + "\n"
        + "\n".join(event.model_dump_json() for event in controller.core.store.events(controller.run_id))
    )


class ProviderFailure(RuntimeError):
    pass


def test_delegate_provider_failure_is_classified_without_persisting_exception_message(monkeypatch):
    controller = _controller()

    async def fail(**kwargs):
        raise ProviderFailure(SECRET)

    monkeypatch.setattr(controller, "_invoke", fail)
    with pytest.raises(AdapterExecutionError) as raised:
        asyncio.run(controller.delegate("task"))

    failure = controller.inspect().failures[-1]
    assert failure.classification == FailureClass.PROVIDER_FAILURE
    assert failure.evidence == (
        "Worker execution failed "
        "[category=PROVIDER_FAILURE; exception_type=ProviderFailure]"
    )
    assert SECRET not in _persisted(controller)
    assert SECRET not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_malformed_structured_output_has_bad_output_taxonomy(monkeypatch):
    controller = _controller()

    async def fail(**kwargs):
        raise SpecialistOutputError(SECRET)

    monkeypatch.setattr(controller, "_invoke", fail)
    with pytest.raises(AdapterExecutionError) as raised:
        asyncio.run(controller.delegate("task"))
    assert controller.inspect().failures[-1].classification == FailureClass.BAD_OUTPUT
    assert SECRET not in _persisted(controller)
    assert raised.value.__cause__ is None and raised.value.__context__ is None


@pytest.mark.parametrize(
    ("error", "expected"),
    [(TimeoutError(SECRET), FailureClass.TIMEOUT),
     (asyncio.CancelledError(SECRET), FailureClass.TIMEOUT)],
)
def test_delegate_timeout_and_cancellation_are_redacted(monkeypatch, error, expected):
    controller = _controller()

    async def fail(**kwargs):
        raise error

    monkeypatch.setattr(controller, "_invoke", fail)
    with pytest.raises(type(error)) as raised:
        asyncio.run(controller.delegate("task"))
    assert controller.inspect().failures[-1].classification == expected
    assert SECRET not in _persisted(controller)
    assert isinstance(raised.value, AdapterExecutionError)
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_review_provider_failure_is_redacted_and_classified(monkeypatch):
    controller = _controller()

    async def author(**kwargs):
        return WorkerResult(
            task_id="task", status="completed", summary="done", deliverable="candidate"
        )

    monkeypatch.setattr(controller, "_invoke", author)
    asyncio.run(controller.delegate("task"))
    controller.validate("task")

    async def fail(**kwargs):
        raise ProviderFailure(SECRET)

    monkeypatch.setattr(controller, "_invoke", fail)
    with pytest.raises(AdapterExecutionError) as raised:
        asyncio.run(controller.review("task"))
    events = controller.core.store.events(controller.run_id)
    failed = [event for event in events if event.kind == "review.failed"][-1]
    assert failed.data["classification"] == FailureClass.PROVIDER_FAILURE.value
    assert failed.data["evidence"] == (
        "Review execution failed "
        "[category=PROVIDER_FAILURE; exception_type=ProviderFailure]"
    )
    assert SECRET not in _persisted(controller)
    assert SECRET not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_direct_review_route_is_assignment_backed_and_bounded():
    controller = _controller(max_review_attempts=1)
    core = controller.core
    assignment = core.delegate(controller.run_id, "task", "author")
    core.start(controller.run_id, "task")
    artifact = core.submit(
        controller.run_id, "task", assignment.id, "author",
        WorkerResult(task_id="task", status="completed", summary="done", deliverable="candidate"),
    )

    core.review(controller.run_id, artifact.id, "reviewer-one", True, "checked")
    run = controller.inspect()
    assert run.tasks["task"].review_attempts == 1
    assert not run.reviews_in_flight
    assert any(event.kind == "review.started" for event in core.store.events(controller.run_id))
    with pytest.raises(GateError, match="attempt limit"):
        core.review(controller.run_id, artifact.id, "reviewer-two", True, "again")
    assert len(controller.inspect().artifacts[artifact.id].reviews) == 1


def test_whitespace_evidence_principals_cannot_create_evidence_or_enable_acceptance():
    controller = _controller()
    core = controller.core
    assignment = core.delegate(controller.run_id, "task", "author")
    core.start(controller.run_id, "task")
    artifact = core.submit(
        controller.run_id, "task", assignment.id, "author",
        WorkerResult(task_id="task", status="completed", summary="done", deliverable="candidate"),
    )

    with pytest.raises(GateError, match="validate own candidate"):
        core.validate(controller.run_id, artifact.id, "result_schema", True, "passed", "   ")
    with pytest.raises(GateError, match="Reviewer must be independent"):
        core.review(controller.run_id, artifact.id, " \t ", True, "checked")

    run = controller.inspect()
    assert not run.artifacts[artifact.id].validations
    assert not run.artifacts[artifact.id].reviews
    assert run.tasks["task"].review_attempts == 0
    assert not run.reviews_in_flight
    with pytest.raises(GateError, match="Validation gates failed"):
        core.accept(controller.run_id, "task", reason="whitespace cannot satisfy QA")
