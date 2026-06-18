import pytest

from cc.tools.dsim.report_tool import GenerateDsimReportTool


@pytest.mark.asyncio
async def test_generate_report_uses_available_summaries() -> None:
    tool = GenerateDsimReportTool()

    result = await tool.execute({"project_id": "project-1", "runs": [{"run_id": "run-1", "status": "completed"}]})

    assert result.is_error is False
    assert "project-1" in result.text
    assert "run-1" in result.text
