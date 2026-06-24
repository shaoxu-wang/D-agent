import pytest

from cc.tools.dsim.report_tool import GenerateDsimReportTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []

    async def generate_report(self, tool_input: dict):
        self.calls.append(tool_input)
        return {"report": "ok"}


@pytest.mark.asyncio
async def test_generate_report_uses_available_summaries() -> None:
    tool = GenerateDsimReportTool()

    result = await tool.execute({"project_id": "project-1", "runs": [{"run_id": "run-1", "status": "completed"}]})

    assert result.is_error is False
    assert "project-1" in result.text
    assert "run-1" in result.text


@pytest.mark.asyncio
async def test_generate_report_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = GenerateDsimReportTool(workflow_service=service)
    payload = {"project_id": "project-1", "runs": [{"run_id": "run-1"}]}

    result = await tool.execute(payload)

    assert result.is_error is False
    assert service.calls == [payload]
