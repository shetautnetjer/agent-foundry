from pydantic import BaseModel, Field


class BuildResult(BaseModel):
    task_id: str
    request_id: str
    success: bool
    files_changed: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    summary: str
    known_issues: list[str] = Field(default_factory=list)
    mock_mode: bool = True


class TestResult(BaseModel):
    task_id: str
    passed: bool
    commands_run: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
