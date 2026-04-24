from typing import Literal

from pydantic import BaseModel, Field


class AgentProfile(BaseModel):
    agent_id: str
    name: str
    role: str
    system_prompt_path: str
    memory_path: str
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_projects: list[str] = Field(default_factory=list)
    can_edit_code: bool = False
    can_approve_own_work: bool = False
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
