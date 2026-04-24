import os
from pathlib import Path


def foundry_home() -> Path:
    return Path(os.environ.get("FOUNDRY_HOME", Path.cwd())).resolve()


def artifact_home() -> Path:
    return Path(os.environ.get("FOUNDRY_RUN_ROOT", foundry_home())).resolve()


def real_codex_enabled() -> bool:
    return os.environ.get("FOUNDRY_ENABLE_REAL_CODEX", "").strip().lower() in {"1", "true", "yes"}


def required_folders() -> list[str]:
    return ["agents", "projects", "policies", "foundry", "prompts"]
