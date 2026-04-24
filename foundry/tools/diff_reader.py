from pathlib import Path


def write_empty_diff(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Mock inspect-only cycle: no diff.\n", encoding="utf-8")
