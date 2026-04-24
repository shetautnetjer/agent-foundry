from pathlib import Path

from typer.testing import CliRunner

from foundry.cli import app


ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_doctor_runs_without_requiring_codex():
    result = runner.invoke(app, ["doctor"], env={"FOUNDRY_HOME": str(ROOT)})

    assert result.exit_code == 0
    assert "Codex installed" in result.stdout


def test_status_and_lists_work():
    env = {"FOUNDRY_HOME": str(ROOT)}

    assert runner.invoke(app, ["status"], env=env).exit_code == 0
    assert runner.invoke(app, ["list-agents"], env=env).exit_code == 0
    assert runner.invoke(app, ["list-projects"], env=env).exit_code == 0


def test_run_cycle_creates_report_and_receipt(tmp_path):
    result = runner.invoke(
        app,
        [
            "run-cycle",
            "--project",
            "ai-trader",
            "--task",
            "Inspect repo and suggest next safe build step",
        ],
        env={"FOUNDRY_HOME": str(ROOT), "FOUNDRY_RUN_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0
    assert "report" in result.stdout.lower()
    assert any((tmp_path / "reports").glob("*.md"))
    assert any((tmp_path / "runs").glob("*/receipt.json"))
