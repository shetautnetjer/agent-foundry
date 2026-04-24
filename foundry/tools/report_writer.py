from __future__ import annotations

from pathlib import Path

from foundry.schemas.reports import CycleReport


class ReportWriter:
    def __init__(self, artifact_home: Path):
        self.report_root = artifact_home / "reports"

    def write(self, report: CycleReport) -> Path:
        self.report_root.mkdir(parents=True, exist_ok=True)
        path = self.report_root / f"{report.task_id}.md"
        lines = [
            f"# {report.title}",
            "",
            f"- Task: `{report.task_id}`",
            f"- Project: `{report.project_id}`",
            f"- Decision: `{report.decision}`",
            f"- Risk: `{report.risk_result}`",
            "",
            "## Summary",
            "",
            report.summary,
            "",
            "## Files Changed",
            "",
        ]
        lines.extend([f"- `{item}`" for item in report.files_changed] or ["- None"])
        lines.extend(["", "## Tests Run", ""])
        lines.extend([f"- `{item}`" for item in report.tests_run] or ["- None"])
        lines.extend(["", "## Next Steps", ""])
        lines.extend([f"- {item}" for item in report.next_steps] or ["- None"])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
