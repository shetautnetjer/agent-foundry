from typing import Literal

from pydantic import BaseModel, Field


class RiskAssessment(BaseModel):
    task_id: str
    approved: bool
    risk_level: Literal["low", "medium", "high", "critical"]
    blocked_reasons: list[str] = Field(default_factory=list)
    mitigations_required: list[str] = Field(default_factory=list)
