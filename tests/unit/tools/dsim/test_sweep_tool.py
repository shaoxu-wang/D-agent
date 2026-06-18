import pytest

from cc.tools.dsim.sweep_tool import RunParameterSweepTool


@pytest.mark.asyncio
async def test_sweep_rejects_more_than_twenty_combinations_without_confirmation() -> None:
    tool = RunParameterSweepTool(invoker=None)
    combinations = [{"value": index} for index in range(21)]

    result = await tool.execute({"handle_id": "h1", "parameter": "R1", "combinations": combinations})

    assert result.is_error is True
    assert "20" in result.text
