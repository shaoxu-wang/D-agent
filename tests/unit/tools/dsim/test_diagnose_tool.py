import pytest

from cc.tools.dsim.diagnose_tool import DiagnoseSimulationFailureTool


@pytest.mark.asyncio
async def test_diagnose_reports_failure_reason() -> None:
    tool = DiagnoseSimulationFailureTool()

    result = await tool.execute({"run_id": "run-1", "status": "failed", "error": {"code": "SIMULATION_FAILED"}})

    assert result.is_error is False
    assert "SIMULATION_FAILED" in result.text
