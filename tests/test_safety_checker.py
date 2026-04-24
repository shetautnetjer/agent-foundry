from foundry.tools.safety_checker import SafetyChecker


def test_safety_checker_blocks_secret_files_and_private_key_text():
    assessment = SafetyChecker().scan(
        task_id="task_1",
        actor_agent="builder",
        changed_files=[".env", "src/app.py"],
        diff_text="+ PRIVATE KEY\n+ seed phrase words\n",
        project_type="generic-python",
    )

    assert assessment.approved is False
    assert "secret-file" in assessment.blocked_reasons
    assert "private-key" in assessment.blocked_reasons
    assert "seed-phrase" in assessment.blocked_reasons


def test_safety_checker_blocks_ai_trader_live_execution_language():
    assessment = SafetyChecker().scan(
        task_id="task_1",
        actor_agent="builder",
        changed_files=["execution.py"],
        diff_text="+ live_trading = True\n+ signTransaction(payload)\n",
        project_type="trading-research",
    )

    assert assessment.approved is False
    assert "live-trading" in assessment.blocked_reasons
    assert "wallet-signing" in assessment.blocked_reasons


def test_safety_checker_blocks_builder_policy_edits():
    assessment = SafetyChecker().scan(
        task_id="task_1",
        actor_agent="builder",
        changed_files=["policies/safety.yaml"],
        diff_text="+ default: allow\n",
        project_type="generic-python",
    )

    assert assessment.approved is False
    assert "builder-policy-edit" in assessment.blocked_reasons
