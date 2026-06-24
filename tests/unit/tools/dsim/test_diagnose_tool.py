import pytest

from cc.tools.dsim.diagnose_tool import DiagnoseSimulationFailureTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []

    async def diagnose_existing(self, tool_input: dict):
        self.calls.append(tool_input)
        return {"diagnosis": "ok"}


@pytest.mark.asyncio
async def test_diagnose_reports_failure_reason() -> None:
    tool = DiagnoseSimulationFailureTool()

    result = await tool.execute({"run_id": "run-1", "status": "failed", "error": {"code": "SIMULATION_FAILED"}})

    assert result.is_error is False
    assert "SIMULATION_FAILED" in result.text


@pytest.mark.asyncio
async def test_diagnose_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = DiagnoseSimulationFailureTool(workflow_service=service)
    payload = {"project_id": "project-1", "run_id": "run-1"}

    result = await tool.execute(payload)

    assert result.is_error is False
    assert service.calls == [payload]
