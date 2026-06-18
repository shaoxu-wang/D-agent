from cc.dsim.registry import has_dsim_mcp_capability, register_dsim_tools
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeDsimMcpTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(content="ok")


def test_register_dsim_tools_requires_mcp_capability() -> None:
    registry = ToolRegistry()

    register_dsim_tools(registry)

    assert has_dsim_mcp_capability(registry) is False
    assert registry.get("RunParameterSweep") is None


def test_register_dsim_tools_when_dsim_mcp_exists() -> None:
    registry = ToolRegistry()
    registry.register(FakeDsimMcpTool())

    register_dsim_tools(registry)

    assert has_dsim_mcp_capability(registry) is True
    assert registry.get("SaveProjectContext") is not None
    assert registry.get("RunParameterSweep") is not None
