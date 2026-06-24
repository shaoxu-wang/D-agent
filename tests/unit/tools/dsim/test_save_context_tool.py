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
    tool = SaveProjectContextTool()

    result = await tool.execute({"kind": "conclusion", "content": "This setup is preferred."})

    assert result.is_error is True
    assert "confirmation" in result.text.lower()


@pytest.mark.asyncio
async def test_save_project_context_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = SaveProjectContextTool(workflow_service=service)

    result = await tool.execute({"project_id": "project-1", "kind": "note", "content": "context"})

    assert result.is_error is False
    assert service.calls == [{"project_id": "project-1", "kind": "note", "content": "context"}]
