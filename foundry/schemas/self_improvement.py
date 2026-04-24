from typing import Literal

from pydantic import BaseModel, Field


class AgentScore(BaseModel):
    agent_id: str
    task_id: str
    score: float
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    recommendation: Literal["keep", "improve", "rollback", "human_review"]


class AgentImprovementProposal(BaseModel):
    proposal_id: str
    agent_id: str
    reason: str
    current_problem: str
    proposed_prompt_patch: str
    expected_benefit: str
    evals_to_run: list[str] = Field(default_factory=list)
    promote_if: list[str] = Field(default_factory=list)
    rollback_if: list[str] = Field(default_factory=list)
