from pathlib import Path

from pydantic import BaseModel


class WorkspaceInfo(BaseModel):
    project_id: str
    task_id: str
    workspace_path: Path
    repo_path: Path
    source_path: Path
    source_exists: bool
    diagnostic: str = ""

    model_config = {"arbitrary_types_allowed": True}
