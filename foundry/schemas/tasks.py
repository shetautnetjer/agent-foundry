from typing import Literal

from pydantic import BaseModel, Field, field_validator

from foundry.schemas.projects import ProjectProfile


class UserIntent(BaseModel):
    raw_text: str
    project_hint: str | None = None
    urgency: Literal["low", "normal", "high"] = "normal"


class WorkRequest(BaseModel):
    request_id: str
    project_id: str
    title: str
    requester_agent: str
    target_agent: str
    reason: str
    requested_change: str
    files_likely_touched: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str]
    tests_required: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high", "critical"]
    requires_human_approval: bool = False

    @field_validator("acceptance_criteria")
    @classmethod
    def acceptance_criteria_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("acceptance_criteria must contain at least one item")
        return value


class TaskPacket(BaseModel):
    task_id: str
    user_intent: UserIntent
    project: ProjectProfile
    selected_agents: list[str]
    work_request: WorkRequest | None = None
    workspace_path: str | None = None
    status: Literal[
        "new",
        "planned",
        "building",
        "testing",
        "risk_review",
        "writing_report",
        "accepted",
        "repair",
        "rejected",
        "human_review",
    ] = "new"
