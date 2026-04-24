from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class ReceiptWriter:
    def __init__(self, artifact_home: Path):
        self.run_root = artifact_home / "runs"

    def write(
        self,
        *,
        task_id: str,
        project_id: str,
        status: str,
        summary: str,
        report_path: str,
    ) -> Path:
        path = self.run_root / task_id / "receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "task_id": task_id,
            "project_id": project_id,
            "status": status,
            "summary": summary,
            "report_path": report_path,
            "created_at": datetime.now(UTC).isoformat(),
            "mock_mode": True,
            "real_codex_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
