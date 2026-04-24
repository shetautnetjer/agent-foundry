import os
from pathlib import Path

import yaml


def foundry_home() -> Path:
    return Path(os.environ.get("FOUNDRY_HOME", Path.cwd())).resolve()


def artifact_home() -> Path:
    return Path(os.environ.get("FOUNDRY_RUN_ROOT", foundry_home())).resolve()


def env_real_codex_enabled() -> bool:
    return os.environ.get("FOUNDRY_ENABLE_REAL_CODEX", "").strip().lower() in {"1", "true", "yes"}


def config_real_codex_enabled(home: Path | None = None) -> bool:
    config_path = (home or foundry_home()) / "foundry.yaml"
    if not config_path.exists():
        return False
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return False
    return bool(data.get("enable_real_codex"))


def real_codex_enabled(home: Path | None = None) -> bool:
    return env_real_codex_enabled() or config_real_codex_enabled(home)


def required_folders() -> list[str]:
    return ["agents", "projects", "policies", "foundry", "prompts"]
