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

    def make_controller(goal, workspace_state_root=None):
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


def test_explicit_registry_recovers_new_startup_without_mutating_retained_state(tmp_path, monkeypatch):
    from walter.sandbox import WorkspaceManager, WorkspaceDependencyMismatch
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    old = tmp_path / "old-env"
    (old / "bin").mkdir(parents=True)
    (old / "bin/python").touch()
    previous = WorkspaceManager(tmp_path, dependency_root=old)
    grant = previous.create_candidate("previous-run", "task", "worker")
    before = previous._manifest.read_bytes()
    with pytest.raises(WorkspaceDependencyMismatch) as error:
        cli._controller("blocked startup")
    assert str(old) in str(error.value)
    assert str(previous.state_root) in str(error.value)
    store = cli._store()
    assert store.list_runs() == []
    store.close()
    fresh = cli._controller("fresh startup", workspace_state_root=".local/fresh-registry")
    run_id = fresh.run_id
    assert fresh.workspaces.state_root == tmp_path / ".local/fresh-registry"
    fresh.close()
    cli._operations(["resume", run_id, "--workspace-state-root", ".local/fresh-registry"])
    assert previous._manifest.read_bytes() == before
    assert (tmp_path / grant.root).exists()
    with pytest.raises(WorkspaceDependencyMismatch):
        cli._controller("default still blocked")


def test_default_registry_does_not_read_readiness_and_rejects_tampering(tmp_path, monkeypatch):
    from walter.sandbox import SandboxViolation
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    readiness = tmp_path / ".local/readiness/retained"
    readiness.mkdir(parents=True)
    (readiness / "grants.json").write_text("invalid retained evidence")
    controller = cli._controller("normal startup")
    assert controller.workspaces.state_root == tmp_path / ".local/sandboxes"
    controller.close()
    (tmp_path / ".local/sandboxes/grants.json").write_text("tampered")
    with pytest.raises(SandboxViolation, match="Invalid workspace grant manifest"):
        cli._controller("must not fallback")
    assert (readiness / "grants.json").read_text() == "invalid retained evidence"


def test_workspace_registry_flag_and_containment(tmp_path, monkeypatch):
    from walter.sandbox import SandboxViolation
    setup_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cli._parser().parse_args(["--workspace-state-root", ".local/fresh", "goal"]).workspace_state_root == ".local/fresh"
    with pytest.raises(SandboxViolation):
        cli._controller("invalid", workspace_state_root=tmp_path.parent / "outside-registry")
    target = tmp_path / ".local/target"
    target.mkdir(parents=True)
    (tmp_path / ".local/link").symlink_to(target, target_is_directory=True)
    with pytest.raises(SandboxViolation, match="Symlinked"):
        cli._controller("invalid", workspace_state_root=".local/link")
