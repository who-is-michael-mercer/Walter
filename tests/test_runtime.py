import asyncio
import json

import pytest

pytest.importorskip("agents")

from agents.tool_context import ToolContext

from walter import runtime


def test_config_requires_openrouter_key():
    with pytest.raises(runtime.RuntimeConfigurationError, match="OPENROUTER_API_KEY"):
        runtime.RuntimeConfig.from_env({})


def test_config_rejects_non_openrouter_provider():
    with pytest.raises(
        runtime.RuntimeConfigurationError,
        match="WALTER_MODEL_PROVIDER.*only 'openrouter'",
    ):
        runtime.RuntimeConfig.from_env(
            {"WALTER_MODEL_PROVIDER": "openai", "OPENROUTER_API_KEY": "test"}
        )


def test_models_are_explicitly_wired_and_tracing_disabled(monkeypatch):
    config = runtime.RuntimeConfig.from_env(
        {
            "OPENROUTER_API_KEY": "test",
            "WALTER_MODEL": "manager",
            "WALTER_WORKER_MODEL": "worker",
        }
    )
    clients = []
    calls = []
    runtime._openrouter_client.cache_clear()

    class FakeClient:
        def __init__(self, **kwargs):
            clients.append(kwargs)

    class FakeModel:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(runtime, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(runtime, "OpenAIChatCompletionsModel", FakeModel)
    monkeypatch.setattr(runtime, "set_tracing_disabled", lambda value: calls.append(value))

    manager, worker = runtime.build_models(config)

    assert manager is not None and worker is not None
    assert calls[0] is True
    assert [call["model"] for call in calls[1:]] == ["manager", "worker"]
    assert all(client["base_url"] == "https://openrouter.ai/api/v1" for client in clients)
    assert all(client["api_key"] == "test" for client in clients)
    assert all(call["should_replay_reasoning_content"](object()) for call in calls[1:])
    assert all(not call["should_replay_reasoning_content"](None) for call in calls[1:])
    assert runtime._should_replay_reasoning_content(object(), "https://openrouter.ai/api/v1/")


def test_default_models_and_reasoning_context():
    config = runtime.RuntimeConfig.from_env({"OPENROUTER_API_KEY": "test"})
    assert config.provider == "openrouter"
    assert config.manager_model == "moonshotai/kimi-k3"
    assert config.worker_model == "moonshotai/kimi-k3"
    assert runtime._should_replay_reasoning_content(object(), config.base_url)
    assert not runtime._should_replay_reasoning_content(None, config.base_url)
    assert not runtime._should_replay_reasoning_content(object(), "http://localhost/v1")


def test_provider_client_is_reused(monkeypatch):
    config = runtime.RuntimeConfig("openrouter", "key", "https://openrouter.ai/api/v1", "m", "w")
    clients = []

    class FakeClient:
        def __init__(self, **kwargs):
            clients.append(kwargs)

    runtime._openrouter_client.cache_clear()
    monkeypatch.setattr(runtime, "AsyncOpenAI", FakeClient)
    runtime._openrouter_model("m", config)
    runtime._openrouter_model("w", config)
    assert len(clients) == 1


def test_manager_uses_manager_model_and_worker_uses_worker_model(monkeypatch):
    config = runtime.RuntimeConfig("openrouter", "key", "https://openrouter.ai/api/v1", "manager", "worker")
    manager_model, worker_model = object(), object()
    agents = []

    monkeypatch.setattr(runtime.RuntimeConfig, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(runtime, "build_models", lambda value: (manager_model, worker_model))
    monkeypatch.setattr(runtime, "_walter_instructions", lambda: "instructions")
    monkeypatch.setattr(
        runtime,
        "_agent",
        lambda **kwargs: agents.append(kwargs) or kwargs,
    )

    manager = runtime.build_walter()
    assert manager["model"] is manager_model
    assert agents[0]["tools"] == [runtime.delegate_task]


def test_manager_uses_durable_controller_when_supplied(monkeypatch):
    class Controller:
        core = object()
        run_id = "run-test"

        def instructions(self):
            return "durable instructions"

        def tools(self):
            return ["durable tool"]

    monkeypatch.setattr(
        runtime.RuntimeConfig,
        "from_env",
        classmethod(lambda cls: runtime.RuntimeConfig(
            "openrouter", "key", "https://openrouter.ai/api/v1", "manager", "worker"
        )),
    )
    monkeypatch.setattr(runtime, "build_models", lambda value: (object(), object()))
    monkeypatch.setattr(runtime, "_agent", lambda **kwargs: kwargs)
    manager = runtime.build_walter(Controller())
    assert manager["instructions"] == "durable instructions"
    assert manager["tools"] == ["durable tool"]


def test_delegate_returns_mocked_structured_tool_continuation(monkeypatch):
    packet = runtime.TaskPacket(
        task_id="t1",
        role="researcher",
        objective="objective",
        deliverable="deliverable",
        acceptance_criteria=["criterion"],
        stop_condition="done",
    )
    expected = runtime.WorkerResult(
        task_id="wrong",
        status="completed",
        summary="ok",
        deliverable="result",
    )
    monkeypatch.setattr(
        runtime.RuntimeConfig,
        "from_env",
        classmethod(lambda cls: runtime.RuntimeConfig("openrouter", "key", "https://openrouter.ai/api/v1", "m", "w")),
    )
    monkeypatch.setattr(runtime, "build_models", lambda config: (object(), object()))
    monkeypatch.setattr(runtime, "_agent", lambda **kwargs: kwargs)

    class Result:
        final_output = expected

    async def fake_run(*args, **kwargs):
        return Result()

    monkeypatch.setattr(runtime.Runner, "run", fake_run)
    # Exercise the SDK's decorated tool callback with its actual invocation context.
    invoke = getattr(runtime.delegate_task, "on_invoke_tool", None)
    if invoke is None:
        pytest.skip("installed SDK does not expose tool invocation hook")
    tool_input = json.dumps({"packet": packet.model_dump()})
    context = ToolContext(
        context=None,
        tool_name="delegate_task",
        tool_call_id="test-call",
        tool_arguments=tool_input,
    )
    result = asyncio.run(invoke(context, tool_input))
    payload = json.loads(result) if isinstance(result, str) else result.model_dump()
    assert payload["task_id"] == "t1"
