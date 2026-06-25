import pytest

from cc.tools.dsim.compare_tool import CompareSimulationRunsTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []

    async def compare_runs(self, tool_input: dict):
        self.calls.append(tool_input)
        return {"comparison": "ok"}


@pytest.mark.asyncio
async def test_compare_requires_two_runs() -> None:
    tool = CompareSimulationRunsTool(workflow_service=object())

    result = await tool.execute({"runs": [{"run_id": "run-1"}]})

    assert result.is_error is True
    assert "two runs" in result.text.lower()


@pytest.mark.asyncio
async def test_compare_requires_workflow_service() -> None:
    tool = CompareSimulationRunsTool()

    result = await tool.execute({"runs": [{"run_id": "run-1"}, {"run_id": "run-2"}]})

    assert result.is_error is True
    assert "workflow service" in result.text.lower()


@pytest.mark.asyncio
async def test_compare_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = CompareSimulationRunsTool(workflow_service=service)
    payload = {"project_id": "project-1", "runs": [{"run_id": "run-1"}, {"run_id": "run-2"}]}

    result = await tool.execute(payload)

    assert result.is_error is False
    assert result.metadata["structured"] == {"comparison": "ok"}
    assert service.calls == [payload]
