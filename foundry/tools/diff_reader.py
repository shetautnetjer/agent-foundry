from pathlib import Path
import difflib

from foundry.tools.workspace_manager import IGNORED_NAMES


def write_empty_diff(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Mock inspect-only cycle: no diff.\n", encoding="utf-8")


def write_workspace_diff(source_path: Path, workspace_path: Path, out_path: Path) -> list[str]:
    changed_files: list[str] = []
    hunks: list[str] = []
    source_files = _text_files(source_path)
    workspace_files = _text_files(workspace_path)
    all_paths = sorted(set(source_files) | set(workspace_files))

    for rel_path in all_paths:
        old = source_files.get(rel_path)
        new = workspace_files.get(rel_path)
        if old == new:
            continue
        changed_files.append(rel_path)
        hunks.extend(_file_patch(rel_path, old, new))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(hunks) if hunks else "# No workspace changes.\n", encoding="utf-8")
    return changed_files


def _text_files(root: Path) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    if not root.exists():
        return files
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_NAMES for part in path.relative_to(root).parts):
            continue
        try:
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
        except UnicodeDecodeError:
            continue
    return files


def _file_patch(rel_path: str, old: list[str] | None, new: list[str] | None) -> list[str]:
    lines = [f"diff --git a/{rel_path} b/{rel_path}\n"]
    if old is None:
        lines.append("new file mode 100644\n")
        fromfile = "/dev/null"
        tofile = f"b/{rel_path}"
        old_lines: list[str] = []
        new_lines = new or []
    elif new is None:
        lines.append("deleted file mode 100644\n")
        fromfile = f"a/{rel_path}"
        tofile = "/dev/null"
        old_lines = old
        new_lines = []
    else:
        fromfile = f"a/{rel_path}"
        tofile = f"b/{rel_path}"
        old_lines = old
        new_lines = new
    lines.extend(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=fromfile,
            tofile=tofile,
        )
    )
    return lines
