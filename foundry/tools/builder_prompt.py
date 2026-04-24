from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_builder_prompt(
    *,
    project_name: str,
    workspace_path: Path,
    work_request: dict[str, Any],
    allowed_files: list[str] | None = None,
    forbidden_changes: list[str] | None = None,
) -> str:
    allowed_files = allowed_files or []
    forbidden_changes = forbidden_changes or []
    return "\n".join(
        [
            "# Builder Agent Task",
            "",
            f"Project: {project_name}",
            f"Workspace: {workspace_path}",
            "",
            "You must operate only inside the workspace path above.",
            "Do not mutate the source project directly.",
            "Do not use danger-full-access.",
            "Do not add secrets.",
            "Do not enable live trading, broker execution, or wallet signing.",
            "Do not auto-commit.",
            "",
            "## WorkRequest",
            "",
            json.dumps(work_request, indent=2, sort_keys=True),
            "",
            "## Allowed Files",
            "",
            "\n".join(f"- {item}" for item in allowed_files) if allowed_files else "- Not specified",
            "",
            "## Forbidden Changes",
            "",
            "\n".join(f"- {item}" for item in forbidden_changes)
            if forbidden_changes
            else "- No secrets",
            "",
            "## Final Output",
            "",
            "Return a concise summary, files changed, tests run, known issues, and next step.",
        ]
    )
