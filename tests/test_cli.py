import json
import subprocess

import pytest

from walter import cli
from walter.orchestration import Orchestrator
from walter.store import SQLiteStore


def setup_repository(tmp_path):
    (tmp_path / "README.md").write_text("# Fixture\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "fixture",
    ], check=True)


def test_offline_run_list_inspect_events_resume_and_approval(tmp_path, monkeypatch, capsys):
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    store = cli._store()
    core = Orchestrator(store)
    run = core.create_run("offline fixture", ["fixture accepted"])
    request = core.request_approval(run.id, "fixture", {"candidate": "one"}, "human boundary")
    store.close()

    cli._operations(["list"])
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["id"] == run.id

    cli._operations(["inspect", run.id])
    assert json.loads(capsys.readouterr().out)["objective"] == "offline fixture"

    cli._operations(["events", run.id])
    assert [event["kind"] for event in json.loads(capsys.readouterr().out)] == [
        "run.created", "approval.required",
    ]

    cli._operations(["resume", run.id])
    assert "Durable status: active" in capsys.readouterr().out

    monkeypatch.setattr(cli.getpass, "getuser", lambda: "fixture-user")
    monkeypatch.setattr(cli.os, "getuid", lambda: 1234)
    cli._operations(["approve", run.id, request.id, "--reason", "scope checked"])
    approved = json.loads(capsys.readouterr().out)
    assert approved["approval_decisions"][request.id]["approved"] is True
    assert approved["approval_decisions"][request.id]["human_id"] == "local-os:fixture-user:uid:1234"


def test_one_shot_builds_manager_around_new_durable_run(monkeypatch, capsys):
    class Run:
        id = "durable-run"
        status = "active"
        final_result = None

    class Controller:
        def inspect(self):
            return Run()

        def close(self):
            observed["closed"] = True

    controller = Controller()
    observed = {}

    def make_controller(goal):
        observed["goal"] = goal
        return controller

    monkeypatch.setattr(cli, "_controller", make_controller)
    monkeypatch.setattr(cli.RuntimeConfig, "from_env", classmethod(lambda cls: object()))
    monkeypatch.setattr(cli, "build_walter", lambda value: observed.setdefault("controller", value) or object())

    async def execute(walter, goal, **kwargs):
        observed["walter"] = walter
        return object(), "trace"

    monkeypatch.setattr(cli, "_execute", execute)
    import asyncio
    asyncio.run(cli._run_once("bounded goal", None, 3))
    assert observed["goal"] == "bounded goal"
    assert observed["controller"] is controller
    assert observed["closed"] is True
    output = capsys.readouterr().out
    assert "Run ID: durable-run" in output
    assert "Local trace ID (provider export disabled): trace" in output


def _stub_run_once(monkeypatch, observed, *, result):
    class Run:
        id = "durable-run"
        status = "active"
        final_result = None

    class Controller:
        def inspect(self):
            return Run()

        def close(self):
            observed["closed"] = True

    monkeypatch.setattr(cli, "_controller", lambda goal: Controller())
    monkeypatch.setattr(cli.RuntimeConfig, "from_env", classmethod(lambda cls: object()))
    monkeypatch.setattr(cli, "build_walter", lambda value: object())

    async def execute(walter, goal, **kwargs):
        return result, "trace"

    monkeypatch.setattr(cli, "_execute", execute)


def test_one_shot_closes_synchronous_session_without_awaiting(monkeypatch):
    observed = {}

    class Session:
        def __init__(self, session_id, db):
            observed["session_id"] = session_id

        def close(self):
            observed["session_closed"] = True

    monkeypatch.setattr(cli, "SQLiteSession", Session)
    _stub_run_once(monkeypatch, observed, result=object())

    import asyncio
    asyncio.run(cli._run_once("bounded goal", "fixture-session", 3))

    assert observed["session_id"] == "fixture-session"
    assert observed["session_closed"] is True


def test_one_shot_prints_manager_final_output(monkeypatch, capsys):
    observed = {}

    class Result:
        final_output = "Run accepted; two tasks remain blocked."

    _stub_run_once(monkeypatch, observed, result=Result())

    import asyncio
    asyncio.run(cli._run_once("bounded goal", None, 3))

    output = capsys.readouterr().out
    assert "Manager: Run accepted; two tasks remain blocked." in output


def test_one_shot_skips_non_string_manager_output(monkeypatch, capsys):
    observed = {}

    class Result:
        final_output = None

    _stub_run_once(monkeypatch, observed, result=Result())

    import asyncio
    asyncio.run(cli._run_once("bounded goal", None, 3))

    assert "Manager:" not in capsys.readouterr().out


def test_legacy_trace_sensitive_flag_is_an_honest_noop(monkeypatch):
    monkeypatch.setenv("OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA", "1")
    args = cli._parser().parse_args(["--trace-sensitive", "goal"])
    assert args.trace_sensitive is True
    cli._configure_trace_privacy(args.trace_sensitive)
    assert cli.os.environ["OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA"] == "0"


def test_missing_provider_config_does_not_create_orphan_run(monkeypatch):
    observed = {"created": False}
    monkeypatch.setattr(
        cli.RuntimeConfig, "from_env",
        classmethod(lambda cls: (_ for _ in ()).throw(cli.RuntimeConfigurationError("missing key"))),
    )
    monkeypatch.setattr(cli, "_controller", lambda goal: observed.update(created=True))
    import asyncio
    with pytest.raises(cli.RuntimeConfigurationError, match="missing key"):
        asyncio.run(cli._run_once("goal", None, 2))
    assert observed["created"] is False


def test_new_cli_run_requires_manager_defined_criteria(tmp_path, monkeypatch):
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    controller = cli._controller("broad objective")
    try:
        assert controller.inspect().plan.completion_criteria == [cli.INITIAL_COMPLETION_CRITERION]
        assert not controller._criteria_defined()
    finally:
        controller.close()


def test_main_reports_missing_run_as_friendly_domain_error(tmp_path, monkeypatch):
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.sys, "argv", ["walter", "run", "inspect", "missing-run"])
    with pytest.raises(SystemExit, match="Walter operation error"):
        cli.main()


def _stub_usage_budget_path(monkeypatch, *, execute):
    class Run:
        id = "durable-run"
        status = "active"
        final_result = None

    class Controller:
        def inspect(self):
            return Run()

        def close(self):
            pass

    monkeypatch.setattr(cli, "_controller", lambda *args, **kwargs: Controller())
    monkeypatch.setattr(cli.RuntimeConfig, "from_env", classmethod(lambda cls: object()))
    monkeypatch.setattr(cli, "build_walter", lambda value: object())
    monkeypatch.setattr(cli, "_execute", execute)


def test_one_shot_reports_usage_budget_exceeded_and_exits_nonzero(monkeypatch, capsys):
    async def execute(walter, goal, **kwargs):
        raise cli.UsageBudgetExceeded("Model-call budget exhausted")

    _stub_usage_budget_path(monkeypatch, execute=execute)

    import asyncio
    with pytest.raises(SystemExit) as excinfo:
        asyncio.run(cli._run_once("bounded goal", None, 3))

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert "Usage budget exceeded: Model-call budget exhausted" in captured.out
    assert "Run ID: durable-run" not in captured.out
    assert "Local trace ID" not in captured.out
    assert "Traceback" not in captured.err


def test_interactive_reports_usage_budget_exceeded_and_continues(monkeypatch, capsys):
    observed = {"closed": 0}

    class Session:
        def __init__(self, session_id, db):
            pass

        async def clear_session(self):
            pass

        def close(self):
            pass

    class Controller:
        def inspect(self):
            raise AssertionError("inspect should not run after budget failure")

        def close(self):
            observed["closed"] += 1

    async def execute(walter, goal, **kwargs):
        raise cli.UsageBudgetExceeded("Model-call budget exhausted")

    monkeypatch.setattr(cli, "SQLiteSession", Session)
    monkeypatch.setattr(cli, "_controller", lambda goal: Controller())
    monkeypatch.setattr(cli.RuntimeConfig, "from_env", classmethod(lambda cls: object()))
    monkeypatch.setattr(cli, "build_walter", lambda value: object())
    monkeypatch.setattr(cli, "_execute", execute)

    responses = iter(["first goal", ":quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    import asyncio
    asyncio.run(cli._run_interactive("fixture-session", 3))

    captured = capsys.readouterr()
    assert "Usage budget exceeded: Model-call budget exhausted" in captured.out
    assert observed["closed"] == 1
