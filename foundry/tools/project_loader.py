from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from foundry.schemas.agents import AgentProfile
from foundry.schemas.projects import ProjectProfile


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"


def load_agents(home: Path) -> list[AgentProfile]:
    agent_root = home / "agents"
    profiles: list[AgentProfile] = []
    for path in sorted(agent_root.glob("*/scorecard.yaml")):
        profiles.append(AgentProfile.model_validate(_read_yaml(path)))
    return profiles


def load_projects(home: Path) -> list[ProjectProfile]:
    project_root = home / "projects"
    profiles: list[ProjectProfile] = []
    for path in sorted(project_root.glob("*.yaml")):
        profiles.append(ProjectProfile.model_validate(_read_yaml(path)))
    return profiles


def find_project(home: Path, project_id: str) -> ProjectProfile | None:
    for project in load_projects(home):
        if project.project_id == project_id or project.name == project_id:
            return project
    return None


def resolve_project_path(home: Path, project: ProjectProfile) -> Path:
    raw = Path(project.repo_path)
    return raw if raw.is_absolute() else (home / raw).resolve()


def register_project(
    home: Path,
    *,
    name: str,
    path: str,
    project_type: str = "generic-python",
) -> Path:
    project_root = home / "projects"
    project_root.mkdir(parents=True, exist_ok=True)
    project_id = _slug(name)
    data = {
        "project_id": project_id,
        "name": name,
        "repo_path": path,
        "project_type": project_type,
        "default_branch": "main",
        "allowed_agents": [
            "orchestra",
            "architect",
            "builder",
            "tester",
            "risk",
            "researcher",
            "writer",
            "critic",
        ],
        "test_commands": ["pytest"],
        "lint_commands": [],
        "safety_notes": ["Registered through Agent Foundry."],
    }
    out = project_root / f"{project_id}.yaml"
    with out.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return out
