import pytest

from cc.tools.dsim.save_context_tool import SaveProjectContextTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []

    async def save_project_context(self, tool_input: dict):
        self.calls.append(tool_input)
        return {"saved": True}


@pytest.mark.asyncio
async def test_save_project_context_requires_confirmation_for_conclusions() -> None:
    tool = SaveProjectContextTool(workflow_service=object())

    result = await tool.execute({"kind": "engineering_conclusion", "content": "This setup is preferred."})

    assert result.is_error is True
    assert "confirmation" in result.text.lower()


def test_save_context_tool_schema_exposes_stage2c_memory_contract() -> None:
    schema = SaveProjectContextTool().get_schema().input_schema
    properties = schema["properties"]

    assert schema["required"] == ["project_id", "kind", "content"]
    assert set(properties["kind"]["enum"]) == {
        "project_fact",
        "user_preference",
        "operating_profile",
        "diagnostic_hint",
        "project_caution",
        "engineering_conclusion",
    }
    assert properties["applies_to"]["type"] == "array"
    assert properties["priority"]["type"] == "integer"


@pytest.mark.asyncio
async def test_save_context_tool_rejects_unsupported_stage2c_kind() -> None:
    result = await SaveProjectContextTool().execute(
        {"project_id": "project-1", "kind": "preference", "content": "old kind", "confirmed": True}
    )

    assert result.is_error is True
    assert "Unsupported DSim memory kind" in result.text


@pytest.mark.asyncio
async def test_save_project_context_requires_workflow_service() -> None:
    tool = SaveProjectContextTool()

    result = await tool.execute({"project_id": "project-1", "kind": "project_fact", "content": "context"})

    assert result.is_error is True
    assert "workflow service" in result.text.lower()


@pytest.mark.asyncio
async def test_save_project_context_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = SaveProjectContextTool(workflow_service=service)

    result = await tool.execute({"project_id": "project-1", "kind": "project_fact", "content": "context"})

    assert result.is_error is False
    assert result.metadata["structured"] == {"saved": True}
    assert service.calls == [{"project_id": "project-1", "kind": "project_fact", "content": "context"}]
