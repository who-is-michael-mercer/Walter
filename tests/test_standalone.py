"""Standalone startup must work using only application files and SDK dependencies."""
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_checkout_has_no_editor_agent_integration():
    assert not (ROOT / "AGENTS.md").exists()
    assert not any(path.is_file() for path in (ROOT / ".codex").rglob("*"))


def test_sdk_and_openrouter_initialize_in_standalone_checkout(tmp_path):
    shutil.copytree(ROOT / "src" / "walter", tmp_path / "src" / "walter",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "SYSTEM_PROMPT.md", tmp_path / "SYSTEM_PROMPT.md")
    result = subprocess.run(
        [sys.executable, "-c", """
import socket

def deny_network(*args, **kwargs):
    raise AssertionError("Standalone initialization must remain offline")

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

from agents import Agent, OpenAIChatCompletionsModel
from walter import adapter, cli, orchestration, runtime
from walter.store import SQLiteStore

config = runtime.RuntimeConfig.from_env()
assert config.provider == 'openrouter'
assert config.base_url == 'https://openrouter.ai/api/v1'
manager_model, worker_model = runtime.build_models(config)
assert isinstance(manager_model, OpenAIChatCompletionsModel)
assert isinstance(worker_model, OpenAIChatCompletionsModel)
core = orchestration.Orchestrator(SQLiteStore())
run = core.create_run('Standalone fixture', ['Fixture accepted'])
controller = adapter.DurableController(core, run.id)
try:
    manager = runtime.build_walter(controller)
    assert isinstance(manager, Agent)
    assert manager.instructions
    assert 'delegate_task' in {tool.name for tool in manager.tools}
finally:
    controller.close()
"""],
        cwd=tmp_path,
        env={"HOME": str(tmp_path), "PYTHONPATH": str(tmp_path / "src"),
             "OPENROUTER_API_KEY": "offline-fixture-key"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
