from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from foundry.config import real_codex_enabled
from foundry.graph.router import route_intent
from foundry.schemas.reports import CycleReport
from foundry.schemas.results import BuildResult
from foundry.schemas.tasks import TaskPacket, UserIntent, WorkRequest
from foundry.storage.events import EventLog
from foundry.tools.builder_prompt import build_builder_prompt
from foundry.tools.codex_runner import CodexRunner
from foundry.tools.diff_reader import write_empty_diff, write_workspace_diff
from foundry.tools.project_loader import find_project, resolve_project_path
from foundry.tools.receipt_writer import ReceiptWriter
from foundry.tools.report_writer import ReportWriter
from foundry.tools.safety_checker import SafetyChecker
from foundry.tools.source_guard import SourceMutationGuard
from foundry.tools.test_runner import mock_test_result
from foundry.tools.workspace_manager import WorkspaceManager


@dataclass(frozen=True)
class CycleArtifacts:
    task_id: str
    report_path: Path
    receipt_path: Path
    decision: str
    summary: str


def make_task_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"task_{stamp}"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_cycle(
    foundry_home: Path,
    artifact_home: Path,
    *,
    project_id: str,
    task: str,
    real_codex_requested: bool = False,
) -> CycleArtifacts:
    task_id = make_task_id()
    run_dir = artifact_home / "runs" / task_id
    event_log = EventLog(run_dir / "events.jsonl")
    event_log.append(
        "cycle_started",
        {"project_id": project_id, "task": task, "real_codex_requested": real_codex_requested},
    )

    project = find_project(foundry_home, project_id)
    if project is None:
        report = CycleReport(
            task_id=task_id,
            project_id=project_id,
            title="Project not registered",
            summary=f"Project `{project_id}` is not registered in projects/.",
            files_changed=[],
            tests_run=[],
            risk_result="not-run",
            decision="human_review",
            next_steps=["Register the project or choose an existing project id."],
        )
        report_path = ReportWriter(artifact_home).write(report)
        receipt_path = ReceiptWriter(artifact_home).write(
            task_id=task_id,
            project_id=project_id,
            status="human_review",
            summary=report.summary,
            report_path=str(report_path.relative_to(artifact_home)),
        )
        return CycleArtifacts(task_id, report_path, receipt_path, "human_review", report.summary)

    route = route_intent(task)
    source_path = resolve_project_path(foundry_home, project)
    workspace = WorkspaceManager(artifact_home / "workspaces").create_workspace(
        project.project_id,
        task_id,
        source_path,
    )

    work_request = WorkRequest(
        request_id=f"req_{task_id}",
        project_id=project.project_id,
        title="Inspect project and suggest next safe build step",
        requester_agent="orchestra",
        target_agent="builder" if real_codex_requested else "architect",
        reason=route.reason,
        requested_change=task,
        files_likely_touched=[],
        acceptance_criteria=[
            "Do not mutate the source project.",
            "Create an inspect-only report and receipt.",
            "Keep mock mode enabled unless real Codex was explicitly requested and enabled.",
        ],
        tests_required=[],
        forbidden_changes=[
            "No live trading.",
            "No broker execution.",
            "No wallet signing.",
            "No direct source repo mutation.",
        ],
        risk_level="low",
    )
    selected_agents = route.selected_agents
    if real_codex_requested and "builder" not in selected_agents:
        selected_agents = [*selected_agents, "builder"]

    packet = TaskPacket(
        task_id=task_id,
        user_intent=UserIntent(raw_text=task, project_hint=project.project_id),
        project=project,
        selected_agents=selected_agents,
        work_request=work_request,
        workspace_path=str(workspace.repo_path),
        status="planned",
    )
    _write_json(run_dir / "task_packet.json", packet.model_dump(mode="json"))
    event_log.append("workspace_created", workspace.model_dump(mode="json"))

    real_enabled = real_codex_enabled(foundry_home)
    prompt = (
        build_builder_prompt(
            project_name=project.name,
            workspace_path=workspace.repo_path,
            work_request=work_request.model_dump(mode="json"),
            allowed_files=work_request.files_likely_touched,
            forbidden_changes=work_request.forbidden_changes,
        )
        if real_codex_requested
        else task
    )
    source_guard = SourceMutationGuard()
    guard_before = None
    guard_report = None
    source_dirty_before_run = False
    if real_codex_requested and real_enabled and workspace.source_exists:
        guard_before = source_guard.capture(source_path)
        source_dirty_before_run = guard_before.dirty

    if source_dirty_before_run:
        build = BuildResult(
            task_id=task_id,
            request_id=work_request.request_id,
            success=False,
            files_changed=[],
            commands_run=[],
            summary="Real Codex refused because the source repo was dirty before the run.",
            known_issues=["source-dirty-before-real-codex"],
            mock_mode=False,
        )
    else:
        build = CodexRunner(foundry_home, allow_real_codex=real_enabled).run_builder(
            task_id=task_id,
            request_id=work_request.request_id,
            workspace_path=workspace.repo_path,
            prompt=prompt,
            real_mode_requested=real_codex_requested,
            run_dir=run_dir,
        )
    event_log.append("builder_result", build.model_dump(mode="json"))

    if guard_before is not None:
        guard_after = source_guard.capture(source_path)
        guard_report = source_guard.compare(guard_before, guard_after)
        source_guard.write_report(run_dir / "source_guard.json", guard_report)
        event_log.append("source_guard", guard_report.__dict__)

    diff_path = run_dir / "diff.patch"
    if real_codex_requested and build.success and workspace.source_exists:
        build.files_changed = write_workspace_diff(source_path, workspace.repo_path, diff_path)
    else:
        write_empty_diff(diff_path)
    risk = SafetyChecker().scan(
        task_id=task_id,
        actor_agent="builder" if real_codex_requested else "orchestra",
        changed_files=build.files_changed,
        diff_text=diff_path.read_text(encoding="utf-8"),
        project_type=project.project_type,
    )
    guard_reasons: list[str] = []
    if source_dirty_before_run:
        guard_reasons.append("source-dirty-before-real-codex")
    if guard_report is not None and guard_report.mutated:
        guard_reasons.append("source-mutation-detected")
    if guard_reasons:
        risk = risk.model_copy(
            update={
                "approved": False,
                "risk_level": "critical",
                "blocked_reasons": sorted(set(risk.blocked_reasons + guard_reasons)),
                "mitigations_required": sorted(
                    set(risk.mitigations_required + ["Review and manually restore source repo state."])
                ),
            }
        )
    _write_json(run_dir / "risk_assessment.json", risk.model_dump(mode="json"))
    event_log.append("risk_assessment", risk.model_dump(mode="json"))

    test_result = mock_test_result(task_id)
    event_log.append("test_result", test_result.model_dump(mode="json"))

    if real_codex_requested and not real_enabled:
        decision = "human_review"
        summary = (
            "Real Codex execution was requested but is disabled. Set "
            "FOUNDRY_ENABLE_REAL_CODEX=1 or foundry.yaml enable_real_codex: true to opt in. "
            "No Codex command ran and no source project files were changed."
        )
    elif not workspace.source_exists:
        decision = "human_review"
        summary = (
            f"Project config loaded, but source path is missing: {workspace.source_path}. "
            "No project code was changed."
        )
    elif risk.approved and build.success:
        decision = "accept"
        if real_codex_requested:
            summary = (
                "Real Codex workspace cycle completed. Codex ran only inside the isolated "
                "workspace, logs and diff were captured, and no source project files were changed."
            )
        else:
            summary = (
                "Mock inspect-only cycle completed. The project was copied into an isolated "
                "workspace, no source files were changed, and no real Codex execution was used."
            )
    else:
        decision = "repair"
        summary = (
            "Real Codex workspace cycle produced findings that require repair before acceptance."
            if real_codex_requested
            else "Mock cycle produced findings that require repair before acceptance."
        )

    report = CycleReport(
        task_id=task_id,
        project_id=project.project_id,
        title="Inspect project and suggest next safe build step",
        summary=summary,
        files_changed=build.files_changed,
        tests_run=test_result.commands_run,
        risk_result="approved" if risk.approved else "blocked",
        decision=decision,
        next_steps=[
            "Review the report and task packet.",
            "Approve a narrow WorkRequest before enabling a real Builder.",
        ],
    )
    report_path = ReportWriter(artifact_home).write(report)
    receipt_path = ReceiptWriter(artifact_home).write(
        task_id=task_id,
        project_id=project.project_id,
        status=decision,
        summary=summary,
        report_path=str(report_path.relative_to(artifact_home)),
        mock_mode=build.mock_mode,
        real_codex_used=bool(build.commands_run),
    )
    event_log.append("cycle_finished", {"decision": decision, "report": str(report_path)})

    return CycleArtifacts(task_id, report_path, receipt_path, decision, summary)
