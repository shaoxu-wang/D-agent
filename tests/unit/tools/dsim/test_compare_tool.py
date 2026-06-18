import pytest

from cc.tools.dsim.compare_tool import CompareSimulationRunsTool


@pytest.mark.asyncio
async def test_compare_requires_two_runs() -> None:
    tool = CompareSimulationRunsTool()

    result = await tool.execute({"runs": [{"run_id": "run-1"}]})

    assert result.is_error is True
    assert "two runs" in result.text.lower()
