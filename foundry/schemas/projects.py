from pydantic import BaseModel, Field


class ProjectProfile(BaseModel):
    project_id: str
    name: str
    repo_path: str
    project_type: str
    default_branch: str = "main"
    allowed_agents: list[str]
    forbidden_paths: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    lint_commands: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
