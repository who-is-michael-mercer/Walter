import json
import subprocess
from pathlib import Path

import pytest

from walter.adapter import DurableController
from walter.orchestration import GateError, Orchestrator
from walter.readiness import run_readiness_demo
from walter.sandbox import CommandResult, SandboxViolation, WorkspaceManager
from walter.store import SQLiteStore


def fixture_repository(tmp_path):
    repository = tmp_path / "fixture"
    repository.mkdir()
    (repository / "README.md").write_text("# Fixture\n")
    (repository / "fixture.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(repository), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "fixture",
    ], check=True)
    return repository


class AvailableWorkspaceManager(WorkspaceManager):
    """Keep orchestration deterministic while asserting the sandbox executor seam is used."""

    def __init__(self, repository):
        super().__init__(repository)
        self.executions = []

    def run_command(self, workspace_id, category, argv, *, worker_id=None, timeout=30):
        self.inspect_grant(workspace_id, worker_id=worker_id)
        self.executions.append((workspace_id, category, list(argv), worker_id))
        return CommandResult(0, "syntax validation passed\n", "")


def test_offline_readiness_stops_at_durable_human_gate(tmp_path):
    repository = fixture_repository(tmp_path)
    database = tmp_path / "operations.db"
    manager = AvailableWorkspaceManager(repository)
    report = run_readiness_demo(repository, store_path=database, workspaces=manager)

    assert manager.executions and manager.executions[0][1] == "test"
    assert report.reloaded
    assert report.pending_human_approval
    assert report.author_id != report.reviewer_id
    assert report.sandbox_validation["returncode"] == 0

    store = SQLiteStore(database)
    run = store.load(report.run_id)
    events = store.events(report.run_id)
    store.close()
    artifact = run.artifacts[report.artifact_id]
    assert run.status == "active"
    assert run.tasks[report.task_id].status == "ACCEPTED"
    assert artifact.status == "accepted"
    assert artifact.validations[-1].passed
    assert artifact.reviews[-1].passed
    assert report.approval_id in run.approvals
    assert report.approval_id not in run.approval_decisions
    assert events[-1].kind == "approval.required"
    assert json.loads(run.approvals[report.approval_id].scope_json) == report.approval_scope


def test_candidate_mutation_invalidates_evidence_and_approval_scope(tmp_path):
    repository = fixture_repository(tmp_path)
    database = tmp_path / "operations.db"
    manager = AvailableWorkspaceManager(repository)
    report = run_readiness_demo(repository, store_path=database, workspaces=manager)
    core = Orchestrator(SQLiteStore(database))
    controller = DurableController(core, report.run_id, manager)

    core.decide_approval(report.run_id, report.approval_id, True, "fixture-human", "exact candidate reviewed")
    assert controller.authorize_candidate_action(
        report.task_id, report.approval_id, "promote_candidate", "stable/main"
    ) == report.approval_scope

    grant = manager.inspect_grant(report.workspace_id)
    readme = Path(grant.root) / "README.md"
    readme.write_text(readme.read_text() + "mutated after evidence\n")
    with pytest.raises(ValueError, match="Candidate changed"):
        controller._fingerprint(report.task_id)
    with pytest.raises(ValueError, match="Candidate changed"):
        controller.authorize_candidate_action(
            report.task_id, report.approval_id, "promote_candidate", "stable/main"
        )

    changed_scope = dict(report.approval_scope, workspace_fingerprint="different")
    with pytest.raises(GateError, match="Exact scoped"):
        core.require_approval(report.run_id, report.approval_id, "promote_candidate", changed_scope)


def test_real_readiness_uses_fail_closed_sandbox(tmp_path):
    repository = fixture_repository(tmp_path)
    report = run_readiness_demo(repository, store_path=tmp_path / "real.db")
    assert report.sandbox_validation["returncode"] == 0


def test_default_readiness_retains_separate_manifests_across_environments(tmp_path, monkeypatch):
    repository = fixture_repository(tmp_path)
    old_environment = tmp_path / "old-environment"
    (old_environment / "bin").mkdir(parents=True)
    (old_environment / "bin/python").touch()
    previous = WorkspaceManager(repository, dependency_root=old_environment)
    previous.create_candidate("previous-run", "previous-task", "previous-author")
    previous_manifest = previous.state_root / "grants.json"
    original_manifest = previous_manifest.read_bytes()

    with pytest.raises(SandboxViolation, match="Workspace dependency environment mismatch"):
        WorkspaceManager(repository)

    def execute(self, workspace_id, category, argv, *, worker_id=None, timeout=30):
        self.inspect_grant(workspace_id, worker_id=worker_id)
        return CommandResult(0, "syntax validation passed\n", "")

    monkeypatch.setattr(WorkspaceManager, "run_command", execute)
    reports = [run_readiness_demo(repository) for _ in range(2)]
    assert reports[0].workspace_state_root != reports[1].workspace_state_root
    assert previous_manifest.read_bytes() == original_manifest
    with pytest.raises(SandboxViolation, match="Workspace dependency environment mismatch"):
        WorkspaceManager(repository)

    store = SQLiteStore(repository / ".local/walter-operations.db")
    try:
        for report in reports:
            retained = WorkspaceManager(repository, state_root=report.workspace_state_root)
            assert retained.inspect_grant(report.workspace_id).run_id == report.run_id
            run = store.load(report.run_id)
            assert report.approval_id not in run.approval_decisions
            assert run.approvals[report.approval_id].status == "pending"
            artifact = run.artifacts[report.artifact_id]
            assert json.loads(artifact.content)["workspace_state_root"] == report.workspace_state_root
    finally:
        store.close()
