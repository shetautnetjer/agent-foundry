from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Annotated

import typer

from foundry.config import artifact_home, foundry_home, real_codex_enabled, required_folders
from foundry.graph.runner import run_cycle
from foundry.tools.project_loader import (
    find_project,
    load_agents,
    load_projects,
    register_project as write_project_config,
    resolve_project_path,
)

app = typer.Typer(help="Agent Foundry V0.1 control CLI.")


def _home() -> Path:
    return foundry_home()


def _artifact_home() -> Path:
    return artifact_home()


@app.command()
def doctor() -> None:
    """Check local wiring without requiring Codex or project repos."""

    home = _home()
    typer.echo(f"Foundry home: {home}")
    typer.echo(f"Python version: {platform.python_version()}")
    major, minor, *_ = platform.python_version_tuple()
    typer.echo(f"Python >= 3.12: {int(major) > 3 or (int(major) == 3 and int(minor) >= 12)}")

    for folder in required_folders():
        typer.echo(f"Required folder {folder}: {(home / folder).exists()}")

    agents = load_agents(home)
    projects = load_projects(home)
    typer.echo(f"Agent profiles valid: {len(agents)}")
    typer.echo(f"Project configs valid: {len(projects)}")

    codex_path = shutil.which("codex")
    typer.echo(f"Codex installed: {bool(codex_path)}")
    if codex_path:
        typer.echo(f"Codex path: {codex_path}")

    ai_trader = find_project(home, "ai-trader")
    if ai_trader is None:
        typer.echo("ai-trader registered: False")
    else:
        path = resolve_project_path(home, ai_trader)
        typer.echo("ai-trader registered: True")
        typer.echo(f"ai-trader path exists: {path.exists()}")
        typer.echo(f"ai-trader path: {path}")

    typer.echo(f"Real Codex enabled: {real_codex_enabled()}")


@app.command()
def status() -> None:
    """Show Foundry status."""

    home = _home()
    agents = load_agents(home)
    projects = load_projects(home)
    typer.echo("Agent Foundry V0.1")
    typer.echo(f"Home: {home}")
    typer.echo(f"Artifact home: {_artifact_home()}")
    typer.echo(f"Agents: {len(agents)}")
    typer.echo(f"Projects: {len(projects)}")
    typer.echo("Mock mode default: True")
    typer.echo(f"Real Codex enabled: {real_codex_enabled()}")


@app.command("list-agents")
def list_agents() -> None:
    """List configured agents."""

    for agent in load_agents(_home()):
        edit = "edit" if agent.can_edit_code else "read-only"
        typer.echo(f"{agent.agent_id}\t{edit}\t{agent.risk_level}\t{agent.role}")


@app.command("list-projects")
def list_projects() -> None:
    """List configured projects without requiring their paths to exist."""

    home = _home()
    for project in load_projects(home):
        path = resolve_project_path(home, project)
        typer.echo(
            f"{project.project_id}\t{project.project_type}\texists={path.exists()}\t{project.repo_path}"
        )


@app.command("register-project")
def register_project(
    name: Annotated[str, typer.Option("--name")],
    path: Annotated[str, typer.Option("--path")],
    project_type: Annotated[str, typer.Option("--project-type")] = "generic-python",
) -> None:
    """Register or overwrite a project config."""

    out = write_project_config(_home(), name=name, path=path, project_type=project_type)
    typer.echo(f"Registered project config: {out}")


@app.command("run-task")
def run_task(
    project: Annotated[str, typer.Option("--project")],
    task: Annotated[str, typer.Option("--task")],
) -> None:
    """Alias for the V0.1 inspect-only cycle."""

    run_cycle_command(project=project, task=task)


@app.command("run-cycle")
def run_cycle_command(
    project: Annotated[str, typer.Option("--project")],
    task: Annotated[str, typer.Option("--task")],
) -> None:
    """Run a mock-safe inspect-only cycle."""

    artifacts = run_cycle(_home(), _artifact_home(), project_id=project, task=task)
    typer.echo(f"Task: {artifacts.task_id}")
    typer.echo(f"Decision: {artifacts.decision}")
    typer.echo(f"Report: {artifacts.report_path}")
    typer.echo(f"Receipt: {artifacts.receipt_path}")


@app.command("report-latest")
def report_latest() -> None:
    """Print the newest report."""

    reports = sorted((_artifact_home() / "reports").glob("*.md"), key=lambda path: path.stat().st_mtime)
    if not reports:
        typer.echo("No reports found.")
        return
    latest = reports[-1]
    typer.echo(f"Latest report: {latest}")
    typer.echo(latest.read_text(encoding="utf-8"))


@app.command("improve-agent")
def improve_agent(agent: Annotated[str, typer.Option("--agent")]) -> None:
    """Create a V0.1 placeholder for the eval-gated improvement loop."""

    known = {profile.agent_id for profile in load_agents(_home())}
    if agent not in known:
        raise typer.BadParameter(f"Unknown agent: {agent}")
    typer.echo(
        f"Improvement loop for `{agent}` is eval-gated and report-only in V0.1. "
        "No prompt files were changed."
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
