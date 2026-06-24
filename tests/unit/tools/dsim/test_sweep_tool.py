import pytest

from cc.tools.dsim.sweep_tool import RunParameterSweepTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []

    async def run_sweep(self, tool_input: dict):
        self.calls.append(tool_input)
        return {"sweep": "ok"}


@pytest.mark.asyncio
async def test_sweep_rejects_more_than_twenty_combinations_without_confirmation() -> None:
    tool = RunParameterSweepTool(workflow_service=None)
    combinations = [{"value": index} for index in range(21)]

    result = await tool.execute({"handle_id": "h1", "parameter": "R1", "combinations": combinations})

    assert result.is_error is True
    assert "20" in result.text


@pytest.mark.asyncio
async def test_sweep_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = RunParameterSweepTool(workflow_service=service)
    payload = {"project_id": "project-1", "combinations": [{"value": 1}], "confirmed": True}

    result = await tool.execute(payload)

    assert result.is_error is False
    assert service.calls == [payload]
