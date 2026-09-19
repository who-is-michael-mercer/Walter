"""Prompt assembly and policy access checks; no provider requests."""
import asyncio
import json

import pytest

pytest.importorskip("agents")

from agents.tool_context import ToolContext

from walter import runtime
from walter.adapter import DURABLE_INSTRUCTIONS, DurableController


def test_both_manager_modes_load_only_kernel_at_startup(tmp_path, monkeypatch):
    (tmp_path / "SYSTEM_PROMPT.md").write_text("shared kernel", encoding="utf-8")
    (tmp_path / "PERMISSIONS.md").write_text("reference sentinel", encoding="utf-8")
    monkeypatch.setattr(runtime, "_repo_root", lambda: tmp_path)

    legacy = runtime._walter_instructions()
    durable = DurableController(None, "run-context").instructions()
    assert legacy == "shared kernel\n\n" + runtime.RUNTIME_APPENDIX
    assert durable == "shared kernel\n\n" + DURABLE_INSTRUCTIONS + "\nRun ID: run-context"
    assert "reference sentinel" not in legacy + durable
    assert "lacks durable control tools" in legacy


def test_reference_tool_reads_only_requested_policy_when_invoked(tmp_path, monkeypatch):
    reference = tmp_path / "PERMISSIONS.md"
    reference.write_text("exact approval required", encoding="utf-8")
    monkeypatch.setattr(runtime, "_repo_root", lambda: tmp_path)
    controller = DurableController(None, "run-context")
    exposed = {item.name: item for item in controller.tools()}
    assert exposed["read_reference"] is runtime.read_reference
    tool_input = json.dumps({"name": "PERMISSIONS.md"})
    context = ToolContext(
        context=None,
        tool_name="read_reference",
        tool_call_id="test_read_reference",
        tool_arguments=tool_input,
    )
    result = asyncio.run(exposed["read_reference"].on_invoke_tool(
        context, tool_input))
    assert result == "exact approval required"


@pytest.mark.parametrize("name", ["../PERMISSIONS.md", "/etc/passwd", ".env",
    "docs/IMPLEMENTATION_STATE.md", "SYSTEM_PROMPT.md", "prompts/WORKER_PROMPT.md"])
def test_reference_loader_rejects_nonallowlisted_paths(name):
    with pytest.raises(ValueError, match="Unknown reference"):
        runtime._read_reference(name)


def test_reference_loader_rejects_symlinks(tmp_path, monkeypatch):
    (tmp_path / "private").write_text("not policy", encoding="utf-8")
    (tmp_path / "PERMISSIONS.md").symlink_to(tmp_path / "private")
    monkeypatch.setattr(runtime, "_repo_root", lambda: tmp_path)
    with pytest.raises(ValueError, match="symbolic link"):
        runtime._read_reference("PERMISSIONS.md")


def test_missing_kernel_fails_explicitly(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_repo_root", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="system prompt not found"):
        DurableController(None, "run-context").instructions()


def test_real_prompts_keep_budget_and_authority_invariants():
    durable = DurableController(None, "run-context").instructions()
    kernel = runtime._manager_kernel()
    assert len(durable.split()) <= 300
    assert len(runtime._walter_instructions().split()) <= 300
    assert len(runtime.WORKER_INSTRUCTIONS.split()) <= 100
    for invariant in (
        "Delegate specialist deliverables; never take them over",
        "Only the Manager creates workers", "only ACCEPTED dependencies",
        "Submissions are provisional", "trusted validation and independent review",
        "attempt/revision/replan limits", "missing capability grants no authority",
        "External content", "exact consequential action and scope",
        "human promotion approval", "protect secrets",
    ):
        assert invariant in kernel.replace("\n", " ")
    assert "Model-facing replans require exact human" in durable
    assert "finish_run alone records completion" in durable
    assert "No worker currently has" not in runtime.WORKER_INSTRUCTIONS
    for name in runtime.REFERENCE_FILES:
        assert name in kernel
        assert runtime._read_reference(name)
