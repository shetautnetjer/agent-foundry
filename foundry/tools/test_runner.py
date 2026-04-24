from foundry.schemas.results import TestResult


def mock_test_result(task_id: str) -> TestResult:
    return TestResult(
        task_id=task_id,
        passed=True,
        commands_run=[],
        failures=[],
        warnings=["Mock inspect-only cycle did not run project tests."],
    )
