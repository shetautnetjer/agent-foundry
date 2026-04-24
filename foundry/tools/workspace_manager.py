from __future__ import annotations

import shutil
from pathlib import Path

from foundry.schemas.workspaces import WorkspaceInfo


IGNORED_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    "data",
    "runs",
    "reports",
    "workspaces",
}


class WorkspaceManager:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def create_workspace(self, project_id: str, task_id: str, source_path: Path) -> WorkspaceInfo:
        workspace_path = self.workspace_root / project_id / task_id
        repo_path = workspace_path / "repo"
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        repo_path.mkdir(parents=True, exist_ok=True)

        source_exists = source_path.exists()
        diagnostic = ""
        if source_exists:
            self._copy_source(source_path, repo_path)
        else:
            diagnostic = f"Project source path is missing: {source_path}"

        return WorkspaceInfo(
            project_id=project_id,
            task_id=task_id,
            workspace_path=workspace_path,
            repo_path=repo_path,
            source_path=source_path,
            source_exists=source_exists,
            diagnostic=diagnostic,
        )

    def _copy_source(self, source_path: Path, repo_path: Path) -> None:
        for child in source_path.iterdir():
            if child.name in IGNORED_NAMES:
                continue
            target = repo_path / child.name
            if child.is_dir():
                shutil.copytree(child, target, ignore=self._ignore)
            else:
                shutil.copy2(child, target)

    @staticmethod
    def _ignore(_: str, names: list[str]) -> set[str]:
        return {name for name in names if name in IGNORED_NAMES or name.endswith(".pyc")}
