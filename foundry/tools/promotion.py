from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PromotionError(RuntimeError):
    """Raised when a promotion gate blocks the task."""


@dataclass(frozen=True)
class ApplyResult:
    task_id: str
    applied: bool
    source_repo: str
    commands_run: list[str]
    message: str


@dataclass(frozen=True)
class DiffSummary:
    task_id: str
    diff_path: Path
    preview: str


class PromotionManager:
    APPROVABLE_STATUSES = {"accept", "accepted", "human_review-approved", "human_review_approved"}

    def __init__(self, foundry_home: Path, artifact_home: Path):
        self.foundry_home = foundry_home
        self.artifact_home = artifact_home
        self.run_root = artifact_home / "runs"

    def latest_diff(self) -> DiffSummary:
        run_dirs = [path for path in self.run_root.glob("*") if path.is_dir()]
        if not run_dirs:
            raise PromotionError("No task runs found.")
        latest = max(run_dirs, key=lambda path: path.stat().st_mtime)
        diff_path = latest / "diff.patch"
        if not diff_path.exists():
            raise PromotionError(f"Latest run has no diff.patch: {latest.name}")
        text = diff_path.read_text(encoding="utf-8", errors="replace")
        preview = "\n".join(text.splitlines()[:40])
        return DiffSummary(task_id=latest.name, diff_path=diff_path, preview=preview)

    def approve_task(self, task_id: str) -> Path:
        bundle = self._load_bundle(task_id)
        if not bundle["risk_assessment"].get("approved"):
            raise PromotionError("Cannot approve task because risk was not approved.")

        status = str(bundle["receipt"].get("status", "")).lower()
        if status not in self.APPROVABLE_STATUSES:
            raise PromotionError(f"Cannot approve task with receipt status `{status}`.")

        approval_path = self._run_dir(task_id) / "approval.json"
        self._write_json(
            approval_path,
            {
                "task_id": task_id,
                "approved": True,
                "created_at": self._now(),
                "requirements_checked": [
                    "task_packet.json",
                    "risk_assessment.json",
                    "receipt.json",
                    "diff.patch",
                    "markdown report",
                    "risk_assessment.approved == true",
                    "receipt status is approvable",
                ],
            },
        )
        return approval_path

    def reject_task(self, task_id: str, reason: str = "") -> Path:
        run_dir = self._run_dir(task_id)
        if not run_dir.exists():
            raise PromotionError(f"Task run does not exist: {task_id}")
        rejection_path = run_dir / "rejection.json"
        self._write_json(
            rejection_path,
            {
                "task_id": task_id,
                "rejected": True,
                "reason": reason,
                "created_at": self._now(),
            },
        )
        return rejection_path

    def apply_approved(self, task_id: str) -> ApplyResult:
        run_dir = self._run_dir(task_id)
        approval_path = run_dir / "approval.json"
        if not approval_path.exists():
            raise PromotionError("Cannot apply task without approval.json.")

        bundle = self._load_bundle(task_id)
        if not bundle["risk_assessment"].get("approved"):
            raise PromotionError("Cannot apply task because risk was not approved.")

        source_repo = self._source_repo(bundle["task_packet"])
        if not source_repo.exists():
            raise PromotionError(f"Project repo path does not exist: {source_repo}")

        diff_path = run_dir / "diff.patch"
        check_command = ["git", "apply", "--check", str(diff_path)]
        apply_command = ["git", "apply", str(diff_path)]

        check = subprocess.run(
            check_command,
            cwd=source_repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if check.returncode != 0:
            detail = (check.stderr or check.stdout).strip()
            raise PromotionError(f"git apply --check failed: {detail}")

        applied = subprocess.run(
            apply_command,
            cwd=source_repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if applied.returncode != 0:
            detail = (applied.stderr or applied.stdout).strip()
            raise PromotionError(f"git apply failed after check passed: {detail}")

        result = ApplyResult(
            task_id=task_id,
            applied=True,
            source_repo=str(source_repo),
            commands_run=["git apply --check diff.patch", "git apply diff.patch"],
            message="Patch applied. No commit was created.",
        )
        self._write_json(
            run_dir / "application.json",
            {
                "task_id": task_id,
                "applied": True,
                "source_repo": str(source_repo),
                "commands_run": result.commands_run,
                "created_at": self._now(),
            },
        )
        return result

    def _load_bundle(self, task_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(task_id)
        if not run_dir.exists():
            raise PromotionError(f"Task run does not exist: {task_id}")

        required = {
            "task_packet": run_dir / "task_packet.json",
            "risk_assessment": run_dir / "risk_assessment.json",
            "receipt": run_dir / "receipt.json",
            "diff": run_dir / "diff.patch",
        }
        missing = [path.name for path in required.values() if not path.exists()]
        if missing:
            raise PromotionError(f"Task is missing required artifacts: {', '.join(missing)}")

        task_packet = self._read_json(required["task_packet"])
        risk_assessment = self._read_json(required["risk_assessment"])
        receipt = self._read_json(required["receipt"])
        report_path = self._report_path(receipt, task_id)
        if not report_path.exists():
            raise PromotionError(f"Task is missing markdown report: {report_path}")

        return {
            "task_packet": task_packet,
            "risk_assessment": risk_assessment,
            "receipt": receipt,
            "report_path": report_path,
        }

    def _source_repo(self, task_packet: dict[str, Any]) -> Path:
        project = task_packet.get("project") or {}
        raw_repo_path = project.get("repo_path")
        if not raw_repo_path:
            raise PromotionError("task_packet.json does not include project.repo_path.")
        repo_path = Path(str(raw_repo_path))
        return repo_path if repo_path.is_absolute() else (self.foundry_home / repo_path).resolve()

    def _report_path(self, receipt: dict[str, Any], task_id: str) -> Path:
        raw = receipt.get("report_path") or f"reports/{task_id}.md"
        path = Path(str(raw))
        return path if path.is_absolute() else self.artifact_home / path

    def _run_dir(self, task_id: str) -> Path:
        return self.run_root / task_id

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
