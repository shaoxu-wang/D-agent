import pytest

from cc.dsim.invoker import DsimToolInvoker
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(
            content="opened",
            metadata={"structured": {"ok": True, "service": "dsim", "tool": "OpenDsimProject"}},
        )


@pytest.mark.asyncio
async def test_invoker_uses_permission_checker_and_registry() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool())
    calls = []

    async def permission_checker(tool_name: str, tool_input: dict) -> bool:
        calls.append((tool_name, tool_input))
        return True

    invoker = DsimToolInvoker(registry=registry, permission_checker=permission_checker)
    result = await invoker.call("mcp__dsim__OpenDsimProject", {"path": "demo.dsim"})

    assert result.content == "opened"
    assert calls == [("mcp__dsim__OpenDsimProject", {"path": "demo.dsim"})]
