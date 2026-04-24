from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSnapshot:
    repos: dict[str, list[str]]

    @property
    def dirty(self) -> bool:
        return any(status for status in self.repos.values())


@dataclass(frozen=True)
class SourceMutationReport:
    baseline_dirty: bool
    mutated: bool
    changed_repos: list[str]
    before: dict[str, list[str]]
    after: dict[str, list[str]]


class SourceMutationGuard:
    """Detect writes to the registered source repo family during workspace runs."""

    def capture(self, source_path: Path) -> SourceSnapshot:
        repos: dict[str, list[str]] = {}
        for repo in self._git_repos(source_path):
            repos[self._relative_repo(source_path, repo)] = self._status(repo)
        return SourceSnapshot(repos=repos)

    def compare(self, before: SourceSnapshot, after: SourceSnapshot) -> SourceMutationReport:
        repo_names = sorted(set(before.repos) | set(after.repos))
        changed = [
            repo for repo in repo_names if before.repos.get(repo, []) != after.repos.get(repo, [])
        ]
        return SourceMutationReport(
            baseline_dirty=before.dirty,
            mutated=bool(changed),
            changed_repos=changed,
            before=before.repos,
            after=after.repos,
        )

    def write_report(self, path: Path, report: SourceMutationReport) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _git_repos(self, source_path: Path) -> list[Path]:
        if not source_path.exists():
            return []
        repos: list[Path] = []
        if self._is_git_repo(source_path):
            repos.append(source_path)
        for child in sorted(source_path.iterdir()):
            if child.is_dir() and self._is_git_repo(child):
                repos.append(child)
        return repos

    @staticmethod
    def _is_git_repo(path: Path) -> bool:
        return (path / ".git").exists()

    @staticmethod
    def _relative_repo(source_path: Path, repo: Path) -> str:
        if repo == source_path:
            return "."
        return repo.relative_to(source_path).as_posix()

    @staticmethod
    def _status(repo: Path) -> list[str]:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            return ["<git-status-error>"]
        return sorted(line for line in proc.stdout.splitlines() if line.strip())
