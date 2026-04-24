import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from foundry.cli import app
from foundry.tools.promotion import PromotionError, PromotionManager


runner = CliRunner()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_foundry_home(tmp_path: Path, *, risk_approved: bool = True) -> tuple[Path, str]:
    home = tmp_path / "foundry"
    artifact_home = tmp_path / "artifacts"
    source_repo = tmp_path / "source"
    source_repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=source_repo, check=True, capture_output=True)
    (source_repo / "README.md").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=source_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=source_repo,
        check=True,
        capture_output=True,
    )

    (home / "projects").mkdir(parents=True)
    (home / "projects" / "demo.yaml").write_text(
        f"""
project_id: demo
name: Demo
repo_path: {source_repo}
project_type: generic-python
allowed_agents:
  - orchestra
""".strip()
        + "\n",
        encoding="utf-8",
    )

    task_id = "task_demo"
    run_dir = artifact_home / "runs" / task_id
    report_path = artifact_home / "reports" / f"{task_id}.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("# Demo Report\n\nDecision: accept\n", encoding="utf-8")

    write_json(
        run_dir / "task_packet.json",
        {
            "task_id": task_id,
            "project": {"project_id": "demo", "repo_path": str(source_repo)},
        },
    )
    write_json(
        run_dir / "risk_assessment.json",
        {"task_id": task_id, "approved": risk_approved, "risk_level": "low", "blocked_reasons": []},
    )
    write_json(
        run_dir / "receipt.json",
        {
            "task_id": task_id,
            "project_id": "demo",
            "status": "accept",
            "report_path": f"reports/{task_id}.md",
        },
    )
    (run_dir / "diff.patch").write_text(
        """diff --git a/README.md b/README.md
index 270a8cc..8327d3c 100644
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-before
+after
""",
        encoding="utf-8",
    )
    return home, task_id


def test_approve_task_writes_approval_when_gates_pass(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    manager = PromotionManager(home, tmp_path / "artifacts")

    approval = manager.approve_task(task_id)

    assert approval.exists()
    data = json.loads(approval.read_text())
    assert data["task_id"] == task_id
    assert data["approved"] is True


def test_reject_task_writes_rejection_without_deleting_artifacts(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    manager = PromotionManager(home, tmp_path / "artifacts")

    rejection = manager.reject_task(task_id, reason="Not the patch we want")

    assert rejection.exists()
    assert (tmp_path / "artifacts" / "runs" / task_id / "diff.patch").exists()
    assert json.loads(rejection.read_text())["rejected"] is True


def test_apply_approved_refuses_without_approval(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    manager = PromotionManager(home, tmp_path / "artifacts")

    try:
        manager.apply_approved(task_id)
    except PromotionError as exc:
        assert "approval" in str(exc).lower()
    else:
        raise AssertionError("apply_approved should require approval.json")


def test_approve_task_refuses_unapproved_risk(tmp_path):
    home, task_id = make_foundry_home(tmp_path, risk_approved=False)
    manager = PromotionManager(home, tmp_path / "artifacts")

    try:
        manager.approve_task(task_id)
    except PromotionError as exc:
        assert "risk" in str(exc).lower()
    else:
        raise AssertionError("approval should require risk approval")


def test_apply_approved_checks_then_applies_patch_to_temp_source_repo(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    artifact_home = tmp_path / "artifacts"
    manager = PromotionManager(home, artifact_home)
    manager.approve_task(task_id)

    result = manager.apply_approved(task_id)

    assert result.applied is True
    assert "git apply --check" in result.commands_run[0]
    source_repo = Path(result.source_repo)
    assert (source_repo / "README.md").read_text(encoding="utf-8") == "after\n"
    assert not (artifact_home / "runs" / task_id / "commit.json").exists()


def test_apply_approved_stops_when_git_apply_check_fails(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    artifact_home = tmp_path / "artifacts"
    run_dir = artifact_home / "runs" / task_id
    (run_dir / "diff.patch").write_text("not a git patch\n", encoding="utf-8")
    manager = PromotionManager(home, artifact_home)
    manager.approve_task(task_id)

    try:
        manager.apply_approved(task_id)
    except PromotionError as exc:
        assert "git apply --check failed" in str(exc)
    else:
        raise AssertionError("invalid patch should stop before apply")


def test_show_latest_diff_cli_prints_newest_diff(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    result = runner.invoke(
        app,
        ["show-latest-diff"],
        env={"FOUNDRY_HOME": str(home), "FOUNDRY_RUN_ROOT": str(tmp_path / "artifacts")},
    )

    assert result.exit_code == 0
    assert task_id in result.stdout
    assert "diff.patch" in result.stdout


def test_approve_and_reject_cli_write_expected_files(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    env = {"FOUNDRY_HOME": str(home), "FOUNDRY_RUN_ROOT": str(tmp_path / "artifacts")}

    approved = runner.invoke(app, ["approve-task", "--task-id", task_id], env=env)
    rejected = runner.invoke(app, ["reject-task", "--task-id", task_id, "--reason", "No"], env=env)

    assert approved.exit_code == 0
    assert rejected.exit_code == 0
    assert (tmp_path / "artifacts" / "runs" / task_id / "approval.json").exists()
    assert (tmp_path / "artifacts" / "runs" / task_id / "rejection.json").exists()


def test_apply_approved_cli_reports_block_without_usage_noise(tmp_path):
    home, task_id = make_foundry_home(tmp_path)
    artifact_home = tmp_path / "artifacts"
    (artifact_home / "runs" / task_id / "diff.patch").write_text(
        "not a git patch\n",
        encoding="utf-8",
    )
    manager = PromotionManager(home, artifact_home)
    manager.approve_task(task_id)

    result = runner.invoke(
        app,
        ["apply-approved", "--task-id", task_id],
        env={"FOUNDRY_HOME": str(home), "FOUNDRY_RUN_ROOT": str(artifact_home)},
    )

    assert result.exit_code == 1
    assert "Blocked:" in result.stdout
    assert "Usage:" not in result.stdout
