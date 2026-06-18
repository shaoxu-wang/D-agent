import pytest

from cc.tools.dsim.save_context_tool import SaveProjectContextTool


@pytest.mark.asyncio
async def test_save_project_context_requires_confirmation_for_conclusions() -> None:
    tool = SaveProjectContextTool()

    result = await tool.execute({"kind": "conclusion", "content": "This setup is preferred."})

    assert result.is_error is True
    assert "confirmation" in result.text.lower()
