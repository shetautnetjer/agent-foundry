import json

from foundry.schemas.reports import CycleReport
from foundry.tools.receipt_writer import ReceiptWriter
from foundry.tools.report_writer import ReportWriter


def test_report_writer_creates_markdown_report(tmp_path):
    report = CycleReport(
        task_id="task_1",
        project_id="ai-trader",
        title="Inspect project",
        summary="Mock inspect-only cycle completed.",
        files_changed=[],
        tests_run=[],
        risk_result="approved",
        decision="accept",
        next_steps=["Review report"],
    )

    path = ReportWriter(tmp_path).write(report)

    text = path.read_text()
    assert "# Inspect project" in text
    assert "Mock inspect-only cycle completed." in text


def test_receipt_writer_creates_json_receipt(tmp_path):
    path = ReceiptWriter(tmp_path).write(
        task_id="task_1",
        project_id="ai-trader",
        status="accepted",
        summary="Inspect-only cycle",
        report_path="reports/task_1.md",
    )

    data = json.loads(path.read_text())
    assert data["task_id"] == "task_1"
    assert data["status"] == "accepted"
