import pytest

from cc.tools.dsim.report_tool import GenerateDsimReportTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []
        self.result = None

    async def generate_report(self, tool_input: dict):
        self.calls.append(tool_input)
        return self.result or {"report": "ok"}


@pytest.mark.asyncio
async def test_generate_report_requires_workflow_service() -> None:
    tool = GenerateDsimReportTool()

    result = await tool.execute({"project_id": "project-1", "runs": [{"run_id": "run-1", "status": "completed"}]})

    assert result.is_error is True
    assert "workflow service" in result.text.lower()


@pytest.mark.asyncio
async def test_generate_report_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = GenerateDsimReportTool(workflow_service=service)
    payload = {"project_id": "project-1", "runs": [{"run_id": "run-1"}]}

    result = await tool.execute(payload)

    assert result.is_error is False
    assert result.metadata["structured"] == {"report": "ok"}
    assert service.calls == [payload]


@pytest.mark.asyncio
async def test_generate_report_marks_failed_workflow_result_as_error() -> None:
    service = FakeWorkflowService()
    service.result = {
        "summary": {"ok": False, "error": "project_id is required"},
        "steps": [{"name": "generate_report", "status": "failed"}],
    }
    tool = GenerateDsimReportTool(workflow_service=service)

    result = await tool.execute({"runs": [{"run_id": "run-1"}]})

    assert result.is_error is True
    assert "failed" in result.text.lower()
    assert "project_id is required" in result.text
