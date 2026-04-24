from pydantic import BaseModel, Field


class CycleReport(BaseModel):
    task_id: str
    project_id: str
    title: str
    summary: str
    files_changed: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    risk_result: str
    decision: str
    next_steps: list[str] = Field(default_factory=list)
