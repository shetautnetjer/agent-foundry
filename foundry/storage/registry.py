from pathlib import Path

from foundry.tools.project_loader import load_agents, load_projects


def registry_counts(home: Path) -> dict[str, int]:
    return {
        "agents": len(load_agents(home)),
        "projects": len(load_projects(home)),
    }
