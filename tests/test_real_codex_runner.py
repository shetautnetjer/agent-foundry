import json
import os
import shlex
import stat
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from foundry.cli import app
from foundry.config import real_codex_enabled
from foundry.graph.runner import run_cycle
from foundry.tools.builder_prompt import build_builder_prompt
from foundry.tools.codex_runner import CodexRunner
from foundry.tools.source_guard import SourceMutationGuard


runner = CliRunner()


def make_project_home(tmp_path: Path) -> tuple[Path, Path, Path]:
    home = tmp_path / "foundry"
    artifact_home = tmp_path / "artifacts"
    source = tmp_path / "source"
    source.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=source, check=True, capture_output=True)
    (source / "README.md").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=source, check=True, capture_output=True)
    (home / "projects").mkdir(parents=True)
    (home / "projects" / "demo.yaml").write_text(
        f"""
project_id: demo
name: Demo
repo_path: {source}
project_type: generic-python
allowed_agents:
  - orchestra
  - architect
  - builder
  - risk
  - writer
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return home, artifact_home, source


def fake_codex(
    bin_dir: Path,
    *,
    exit_code: int = 0,
    mutate_workspace: bool = False,
    mutate_source: Path | None = None,
) -> Path:
    codex = bin_dir / "codex"
    mutation = "printf 'after\\n' > README.md" if mutate_workspace else ":"
    source_mutation = (
        f"printf 'source-after\\n' > {shlex.quote(str(mutate_source / 'README.md'))}"
        if mutate_source is not None
        else ":"
    )
    codex.write_text(
        f"""#!/usr/bin/env bash
set -u
workspace=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-C" ]; then
    shift
    workspace="$1"
  fi
  shift || true
done
cd "$workspace"
{mutation}
{source_mutation}
cat >/dev/null
printf '{{"event":"done"}}\\n'
printf 'fake stderr\\n' >&2
exit {exit_code}
""",
        encoding="utf-8",
    )
    codex.chmod(codex.stat().st_mode | stat.S_IXUSR)
    return codex


def test_real_codex_config_requires_env_or_config(tmp_path, monkeypatch):
    monkeypatch.delenv("FOUNDRY_ENABLE_REAL_CODEX", raising=False)
    assert real_codex_enabled(tmp_path) is False

    (tmp_path / "foundry.yaml").write_text("enable_real_codex: true\n", encoding="utf-8")

    assert real_codex_enabled(tmp_path) is True


def test_codex_runner_command_uses_workspace_and_never_danger_full_access(tmp_path):
    command = CodexRunner(foundry_home=tmp_path).build_command(
        tmp_path / "workspace",
        codex_path="codex",
    )

    assert command == [
        "codex",
        "exec",
        "--full-auto",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--json",
        "-C",
        str(tmp_path / "workspace"),
        "-",
    ]
    assert "danger-full-access" not in " ".join(command)
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


def test_real_codex_runner_writes_logs_and_returns_failure_without_throwing(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_codex(bin_dir, exit_code=7)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_dir = tmp_path / "runs" / "task_1"

    result = CodexRunner(foundry_home=tmp_path, allow_real_codex=True).run_builder(
        task_id="task_1",
        request_id="req_1",
        workspace_path=workspace,
        prompt="do work",
        real_mode_requested=True,
        run_dir=run_dir,
    )

    assert result.success is False
    assert result.mock_mode is False
    assert (run_dir / "codex_stdout.jsonl").read_text(encoding="utf-8").strip()
    assert "fake stderr" in (run_dir / "codex_stderr.log").read_text(encoding="utf-8")


def test_real_codex_run_cycle_refuses_without_opt_in_and_creates_report(tmp_path, monkeypatch):
    home, artifact_home, source = make_project_home(tmp_path)
    monkeypatch.delenv("FOUNDRY_ENABLE_REAL_CODEX", raising=False)

    artifacts = run_cycle(
        home,
        artifact_home,
        project_id="demo",
        task="Try real codex",
        real_codex_requested=True,
    )

    assert artifacts.decision == "human_review"
    assert "disabled" in artifacts.summary.lower()
    assert (artifact_home / "runs" / artifacts.task_id / "receipt.json").exists()
    assert (source / "README.md").read_text(encoding="utf-8") == "before\n"


def test_real_codex_run_cycle_uses_workspace_and_captures_diff_without_source_mutation(
    tmp_path,
    monkeypatch,
):
    home, artifact_home, source = make_project_home(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_codex(bin_dir, exit_code=0, mutate_workspace=True)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FOUNDRY_ENABLE_REAL_CODEX", "1")

    artifacts = run_cycle(
        home,
        artifact_home,
        project_id="demo",
        task="Make a tiny docs-only change in the workspace and produce a diff",
        real_codex_requested=True,
    )

    run_dir = artifact_home / "runs" / artifacts.task_id
    assert artifacts.decision == "accept"
    assert (run_dir / "codex_stdout.jsonl").exists()
    assert "+after" in (run_dir / "diff.patch").read_text(encoding="utf-8")
    assert (source / "README.md").read_text(encoding="utf-8") == "before\n"
    receipt = json_load(run_dir / "receipt.json")
    assert receipt["real_codex_used"] is True
    assert receipt["mock_mode"] is False


def test_source_guard_detects_nested_repo_mutation(tmp_path):
    home, _artifact_home, source = make_project_home(tmp_path)
    nested = source / "nested-core"
    nested.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=nested, check=True, capture_output=True)
    (nested / "core.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "core.txt"], cwd=nested, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=nested, check=True, capture_output=True)

    guard = SourceMutationGuard()
    before = guard.capture(source)
    (nested / "core.txt").write_text("after\n", encoding="utf-8")
    after = guard.capture(source)
    report = guard.compare(before, after)
    out = home / "runs" / "task_1" / "source_guard.json"
    guard.write_report(out, report)

    payload = json_load(out)
    assert report.mutated is True
    assert "nested-core" in report.changed_repos
    assert payload["mutated"] is True
    assert str(source) not in out.read_text(encoding="utf-8")


def test_real_codex_run_cycle_blocks_if_source_repo_is_mutated(tmp_path, monkeypatch):
    home, artifact_home, source = make_project_home(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_codex(bin_dir, exit_code=0, mutate_workspace=True, mutate_source=source)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FOUNDRY_ENABLE_REAL_CODEX", "1")

    artifacts = run_cycle(
        home,
        artifact_home,
        project_id="demo",
        task="Make a workspace change",
        real_codex_requested=True,
    )

    run_dir = artifact_home / "runs" / artifacts.task_id
    risk = json_load(run_dir / "risk_assessment.json")
    guard = json_load(run_dir / "source_guard.json")
    receipt = json_load(run_dir / "receipt.json")

    assert artifacts.decision == "repair"
    assert risk["approved"] is False
    assert "source-mutation-detected" in risk["blocked_reasons"]
    assert guard["mutated"] is True
    assert "." in guard["changed_repos"]
    assert receipt["status"] == "repair"
    assert (source / "README.md").read_text(encoding="utf-8") == "source-after\n"


def test_real_codex_run_cycle_failure_still_writes_logs_report_and_receipt(
    tmp_path,
    monkeypatch,
):
    home, artifact_home, source = make_project_home(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_codex(bin_dir, exit_code=7, mutate_workspace=False)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FOUNDRY_ENABLE_REAL_CODEX", "1")

    artifacts = run_cycle(
        home,
        artifact_home,
        project_id="demo",
        task="Try a failing Codex run",
        real_codex_requested=True,
    )

    run_dir = artifact_home / "runs" / artifacts.task_id
    assert artifacts.decision == "repair"
    assert (run_dir / "codex_stdout.jsonl").exists()
    assert (run_dir / "codex_stderr.log").exists()
    assert artifacts.report_path.exists()
    receipt = json_load(run_dir / "receipt.json")
    assert receipt["real_codex_used"] is True
    assert (source / "README.md").read_text(encoding="utf-8") == "before\n"


def test_codex_status_works_without_codex_on_path(tmp_path):
    (tmp_path / "projects").mkdir()
    result = runner.invoke(
        app,
        ["codex-status"],
        env={"FOUNDRY_HOME": str(tmp_path), "PATH": ""},
    )

    assert result.exit_code == 0
    assert "Codex found: False" in result.stdout
    assert "danger-full-access blocked: True" in result.stdout


def test_builder_prompt_contains_work_request_and_safety_rules(tmp_path):
    prompt = build_builder_prompt(
        project_name="Demo",
        workspace_path=tmp_path / "workspace",
        work_request={"title": "Docs only", "forbidden_changes": ["No live trading"]},
        allowed_files=["README.md"],
        forbidden_changes=["No secrets"],
    )

    assert "Demo" in prompt
    assert str(tmp_path / "workspace") in prompt
    assert "No live trading" in prompt
    assert "No secrets" in prompt
    assert "README.md" in prompt


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
