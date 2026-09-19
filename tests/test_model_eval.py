import pytest

pytest.importorskip("agents")

from walter import model_eval


def catalog():
    return {"data": [{"id": model, "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                      "supported_parameters": ["max_tokens", "reasoning"]}
                     for model in model_eval.MODELS]}


def test_plan_rejects_missing_model_and_expensive_time_override():
    data = catalog()
    assert len(model_eval.validate_plan(data)) == 2
    data["data"].pop()
    with pytest.raises(ValueError, match="unavailable"):
        model_eval.validate_plan(data)
    data = catalog()
    data["data"][0]["pricing"]["overrides"] = [{"completion": "0.01"}]
    with pytest.raises(ValueError, match="ceiling"):
        model_eval.validate_plan(data)


def test_eval_disables_retries_and_fallbacks_and_caps_cost():
    settings = model_eval.request_settings()
    assert settings.max_tokens == 1024
    assert settings.retry.max_retries == 0
    assert settings.extra_body["provider"]["allow_fallbacks"] is False
    assert model_eval.MAX_CALLS * model_eval.CALL_RESERVE < model_eval.SOFT_BUDGET


def test_oracle_rejects_provisional_dependency_and_bad_review():
    assert model_eval.accepted("reasoning", '{"ready":["B"],"blocked":["C","D"]}')
    assert not model_eval.accepted("reasoning", '{"ready":["B","D"],"blocked":["C"]}')
    assert not model_eval.accepted("review", '{"accept":true}')
    assert not model_eval.accepted("implementation", 'not JSON')


def test_provider_error_stops_without_retry_and_redacts_exception(monkeypatch):
    import asyncio
    from walter.runtime import RuntimeConfig

    class PrivateClient:
        async def close(self):
            pass

    calls = []

    async def fail(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("SECRET should never be in the report")

    client = lambda config: PrivateClient()
    client.cache_clear = lambda: None
    monkeypatch.setattr(model_eval.RuntimeConfig, "from_env", classmethod(
        lambda cls: RuntimeConfig("openrouter", "SECRET", model_eval.DEFAULT_OPENROUTER_BASE_URL, "m", "w")))
    monkeypatch.setattr(model_eval, "fetch_catalog", catalog)
    monkeypatch.setattr(model_eval, "build_models", lambda config: (object(), object()))
    monkeypatch.setattr(model_eval, "Agent", lambda **kwargs: object())
    monkeypatch.setattr(model_eval.Runner, "run", fail)
    monkeypatch.setattr(model_eval, "_openrouter_client", client)
    report = asyncio.run(model_eval.evaluate())
    assert len(calls) == 1
    assert report["stop_reason"] == "availability_uncertain_no_retry"
    assert report["reserved_usd"] == model_eval.CALL_RESERVE
    assert "SECRET" not in str(report)
