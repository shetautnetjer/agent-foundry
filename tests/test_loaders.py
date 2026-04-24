from pathlib import Path

from foundry.tools.project_loader import load_agents, load_projects, register_project


ROOT = Path(__file__).resolve().parents[1]


def test_load_agents_reads_required_profiles():
    agents = load_agents(ROOT)
    ids = {agent.agent_id for agent in agents}

    assert {"orchestra", "architect", "builder", "tester", "risk", "writer", "critic"} <= ids
    builder = next(agent for agent in agents if agent.agent_id == "builder")
    assert builder.can_edit_code is True
    assert builder.can_approve_own_work is False


def test_load_projects_does_not_require_repo_paths_to_exist(tmp_path):
    project_dir = tmp_path / "projects"
    project_dir.mkdir()
    (project_dir / "missing.yaml").write_text(
        """
project_id: missing
name: Missing Repo
repo_path: ../does-not-exist
project_type: generic-python
allowed_agents:
  - orchestra
""".strip()
    )

    projects = load_projects(tmp_path)

    assert projects[0].project_id == "missing"
    assert projects[0].repo_path == "../does-not-exist"


def test_register_project_writes_project_config(tmp_path):
    register_project(
        tmp_path,
        name="demo",
        path="../demo",
        project_type="generic-python",
    )

    projects = load_projects(tmp_path)
    assert projects[0].project_id == "demo"
    assert projects[0].repo_path == "../demo"
