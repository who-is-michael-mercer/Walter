"""Offline end-to-end proof of the durable Manager loop through finish_run."""
import asyncio
import json

from agents import Runner, set_tracing_disabled

from fakes import message_step, responder_step, scripted_model, tool_step
from walter import runtime
from walter.adapter import INITIAL_COMPLETION_CRITERION, DurableController
from walter.orchestration import Orchestrator
from walter.store import SQLiteStore

CRITERION = "Demo artifact accepted with trusted validation and independent review evidence"

PACKET = {
    "task_id": "a",
    "role": "demo specialist",
    "objective": "Produce the demo deliverable",
    "deliverable": "A short demo deliverable document",
    "acceptance_criteria": ["Deliverable states the demo outcome"],
    "stop_condition": "Deliverable returned or genuinely blocked",
}

WORKER_RESULT = {
    "task_id": "a",
    "status": "completed",
    "summary": "Demo deliverable produced",
    "deliverable": "Demo deliverable: objective met.",
    "evidence": ["Deliverable drafted from the task packet"],
    "acceptance_check": [{
        "criterion": "Deliverable states the demo outcome",
        "passed": True,
        "note": "Stated in the deliverable",
    }],
}

REVIEW_RESULT = {
    "passed": True,
    "evidence": ["Deliverable matches the packet objective"],
    "reason": "Evidence satisfies the acceptance criteria",
}


def _offline_config():
    return runtime.RuntimeConfig(
        provider="openrouter", api_key="offline-fixture",
        base_url="https://openrouter.ai/api/v1",
        manager_model="fake-manager", worker_model="fake-worker", budget=None)


def test_durable_manager_loop_completes_offline(tmp_path, monkeypatch):
    set_tracing_disabled(True)
    store = SQLiteStore(tmp_path / "operations.db")
    core = Orchestrator(store)
    run = core.create_run("Offline demo objective", [INITIAL_COMPLETION_CRITERION])
    controller = DurableController(core, run.id)

    def finish_step(call):
        # Computed at call time: the artifact ID only exists after acceptance.
        state = controller.inspect()
        artifact_id = state.tasks["a"].artifact_ids[-1]
        return tool_step("finish_run", {
            "summary": "Demo run completed with an accepted artifact.",
            "criterion_evidence_json": json.dumps({CRITERION: [artifact_id]}),
        }, call_id="call-finish")

    manager = scripted_model([
        tool_step("set_completion_criteria", {"criteria": [CRITERION]}, call_id="call-criteria"),
        tool_step("plan_tasks", {"packets": [PACKET], "capabilities": ["model_only"],
                                 "checks": [["result_schema"]]}, call_id="call-plan"),
        tool_step("delegate_task", {"task_id": "a"}, call_id="call-delegate"),
        tool_step("validate_task", {"task_id": "a"}, call_id="call-validate"),
        tool_step("review_task", {"task_id": "a"}, call_id="call-review"),
        tool_step("accept_task", {"task_id": "a",
                                  "reason": "Trusted validation and independent review passed"},
                  call_id="call-accept"),
        responder_step(finish_step),
        message_step("Run completed; demo artifact accepted."),
    ])
    worker = scripted_model([
        message_step(json.dumps(WORKER_RESULT)),
        message_step(json.dumps(REVIEW_RESULT)),
    ])

    monkeypatch.setattr(runtime.RuntimeConfig, "from_env",
                        classmethod(lambda cls: _offline_config()))
    monkeypatch.setattr(runtime, "build_models", lambda config: (manager, worker))

    agent = runtime.build_walter(controller)
    result = asyncio.run(Runner.run(agent, input="Run the offline demo", max_turns=20))

    assert result.final_output == "Run completed; demo artifact accepted."
    final = controller.inspect()
    assert final.status == "completed"
    task = final.tasks["a"]
    assert task.status == "ACCEPTED"
    artifact = final.artifacts[task.artifact_ids[-1]]
    assert artifact.status == "accepted"

    kinds = [event.kind for event in store.events(run.id)]
    for expected in ("run.created", "plan.criteria_defined", "task.created",
                     "assignment.created", "assignment.started", "artifact.submitted",
                     "artifact.validation_completed", "artifact.reviewed",
                     "artifact.accepted", "run.completed"):
        assert expected in kinds, expected

    assert final.usage_records, "durable usage accounting persisted no records"
    assert all(record.usage_known for record in final.usage_records)
    assert {record.role for record in final.usage_records} == {"manager", "worker", "reviewer"}
    assert all(record.input_tokens == 11 and record.output_tokens == 7
               for record in final.usage_records)

    manager.assert_complete()
    worker.assert_complete()
    controller.close()
