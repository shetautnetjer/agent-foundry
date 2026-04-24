from pydantic import ValidationError

from foundry.schemas.agents import AgentProfile
from foundry.schemas.projects import ProjectProfile
from foundry.schemas.tasks import TaskPacket, UserIntent, WorkRequest


def test_agent_profile_prevents_self_approval_for_builder_shape():
    profile = AgentProfile(
        agent_id="builder",
        name="Builder Agent",
        role="Writes approved code changes",
        system_prompt_path="agents/builder/system.md",
        memory_path="agents/builder/memory.md",
        allowed_tools=["codex_runner"],
        allowed_projects=["ai-trader"],
        can_edit_code=True,
        can_approve_own_work=False,
        risk_level="high",
    )

    assert profile.can_edit_code is True
    assert profile.can_approve_own_work is False


def test_work_request_requires_acceptance_criteria():
    with pytest_raises_validation_error():
        WorkRequest(
            request_id="req_1",
            project_id="ai-trader",
            title="Missing acceptance",
            requester_agent="architect",
            target_agent="builder",
            reason="No criteria should be rejected",
            requested_change="Do something",
            acceptance_criteria=[],
            risk_level="medium",
        )


def test_task_packet_status_defaults_to_new():
    project = ProjectProfile(
        project_id="example",
        name="Example",
        repo_path="../example",
        project_type="generic-python",
        allowed_agents=["orchestra", "architect"],
    )
    packet = TaskPacket(
        task_id="task_20260424_000001",
        user_intent=UserIntent(raw_text="Inspect the repo"),
        project=project,
        selected_agents=["orchestra", "architect"],
    )

    assert packet.status == "new"


class pytest_raises_validation_error:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        assert exc_type is ValidationError
        return True
