from foundry.tools.codex_runner import CodexRunner


def test_codex_runner_defaults_to_mock_mode(tmp_path):
    runner = CodexRunner(foundry_home=tmp_path)

    result = runner.run_builder(
        task_id="task_1",
        request_id="req_1",
        workspace_path=tmp_path,
        prompt="Do inspect-only work",
    )

    assert result.success is True
    assert result.files_changed == []
    assert result.mock_mode is True


def test_codex_runner_refuses_real_mode_without_explicit_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("FOUNDRY_ENABLE_REAL_CODEX", raising=False)
    runner = CodexRunner(foundry_home=tmp_path, allow_real_codex=False)

    result = runner.run_builder(
        task_id="task_1",
        request_id="req_1",
        workspace_path=tmp_path / "workspace",
        prompt="Try real work",
        real_mode_requested=True,
    )

    assert result.success is False
    assert "disabled" in result.summary.lower()
    assert result.mock_mode is False
