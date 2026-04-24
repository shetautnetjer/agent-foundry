from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from foundry.schemas.results import BuildResult


class CodexRunner:
    def __init__(self, foundry_home: Path, allow_real_codex: bool | None = None):
        self.foundry_home = foundry_home
        self.allow_real_codex = (
            os.environ.get("FOUNDRY_ENABLE_REAL_CODEX", "").lower() in {"1", "true", "yes"}
            if allow_real_codex is None
            else allow_real_codex
        )

    def run_builder(
        self,
        *,
        task_id: str,
        request_id: str,
        workspace_path: Path,
        prompt: str,
        real_mode_requested: bool = False,
        run_dir: Path | None = None,
    ) -> BuildResult:
        if not real_mode_requested:
            return BuildResult(
                task_id=task_id,
                request_id=request_id,
                success=True,
                files_changed=[],
                commands_run=[],
                summary="Mock inspect-only builder result. No project files were changed.",
                known_issues=[],
                mock_mode=True,
            )

        if not self.allow_real_codex:
            return BuildResult(
                task_id=task_id,
                request_id=request_id,
                success=False,
                files_changed=[],
                commands_run=[],
                summary="Real Codex execution is disabled. Set FOUNDRY_ENABLE_REAL_CODEX=1 to opt in.",
                known_issues=["real-codex-disabled"],
                mock_mode=False,
            )

        codex_path = shutil.which("codex")
        stdout_path, stderr_path = self._log_paths(run_dir)
        if codex_path is None:
            self._write_logs(stdout_path, stderr_path, "", "codex executable was not found on PATH\n")
            return BuildResult(
                task_id=task_id,
                request_id=request_id,
                success=False,
                files_changed=[],
                commands_run=[],
                summary="Real Codex execution requested, but codex is not installed.",
                known_issues=["codex-not-installed"],
                mock_mode=False,
                stdout_path=str(stdout_path) if stdout_path else None,
                stderr_path=str(stderr_path) if stderr_path else None,
            )

        command = self.build_command(workspace_path, codex_path=codex_path)
        proc = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
        )
        self._write_logs(stdout_path, stderr_path, proc.stdout, proc.stderr)
        events = [line for line in proc.stdout.splitlines() if line.strip()]
        summary = "Real Codex execution completed." if proc.returncode == 0 else "Real Codex failed."
        known_issues = [] if proc.returncode == 0 else [proc.stderr.strip() or "codex-exec-failed"]
        return BuildResult(
            task_id=task_id,
            request_id=request_id,
            success=proc.returncode == 0,
            files_changed=[],
            commands_run=[" ".join(command)],
            summary=f"{summary} Captured {len(events)} JSONL events.",
            known_issues=known_issues,
            mock_mode=False,
            stdout_path=str(stdout_path) if stdout_path else None,
            stderr_path=str(stderr_path) if stderr_path else None,
        )

    @staticmethod
    def build_command(workspace_path: Path, *, codex_path: str = "codex") -> list[str]:
        return [
            codex_path,
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
            str(workspace_path),
            "-",
        ]

    @staticmethod
    def _log_paths(run_dir: Path | None) -> tuple[Path | None, Path | None]:
        if run_dir is None:
            return None, None
        return run_dir / "codex_stdout.jsonl", run_dir / "codex_stderr.log"

    @staticmethod
    def _write_logs(
        stdout_path: Path | None,
        stderr_path: Path | None,
        stdout: str,
        stderr: str,
    ) -> None:
        if stdout_path is not None:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text(stdout, encoding="utf-8")
        if stderr_path is not None:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(stderr, encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
