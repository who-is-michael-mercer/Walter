from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TaskPacket(BaseModel):
    """The minimum-sufficient assignment Walter gives one temporary specialist."""

    task_id: str = Field(description="Stable identifier assigned by Walter for this task.")
    role: str = Field(description="Narrow specialist role for this single lane of work.")
    objective: str = Field(description="The one objective this worker must accomplish.")
    deliverable: str = Field(description="The inspectable output the worker must return.")
    context: str = Field(
        default="",
        description="Only the goal context and accepted upstream information needed for this lane.",
    )
    required_inputs: list[str] = Field(
        default_factory=list,
        description="Inputs the worker must use or account for.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Scope, policy, format, or implementation constraints for this task.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Accepted upstream task or artifact identifiers this task depends on.",
    )
    acceptance_criteria: list[str] = Field(
        min_length=1,
        description="Criteria Walter will use to accept or reject the deliverable.",
    )
    stop_condition: str = Field(
        description="Condition telling the worker when its lane is complete or genuinely blocked."
    )
    tool_policy: Literal["model_only"] = Field(
        default="model_only",
        description=(
            "Tools granted to this worker. The initial runtime intentionally supports only "
            "model reasoning and structured output."
        ),
    )


class CriterionCheck(BaseModel):
    criterion: str
    passed: bool
    note: str = ""


class WorkerResult(BaseModel):
    """Structured, provisional worker output returned to Walter for acceptance review."""

    task_id: str
    status: Literal["completed", "blocked", "needs_revision"]
    summary: str
    deliverable: str
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    acceptance_check: list[CriterionCheck] = Field(default_factory=list)
    blocker: str | None = None
    specialist_request: str | None = Field(
        default=None,
        description="A specialty this worker believes Walter should create, if one is required.",
    )
