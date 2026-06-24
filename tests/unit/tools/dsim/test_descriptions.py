from cc.dsim.registry import register_dsim_tools
from cc.dsim.runtime import DsimRuntimeBundle
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeDsimMcpTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(content="ok")


def test_dsim_tool_descriptions_guide_layered_usage() -> None:
    registry = ToolRegistry()
    registry.register(FakeDsimMcpTool())
    register_dsim_tools(
        registry,
        runtime=DsimRuntimeBundle(
            registry=registry,
            permission_ctx=object(),
            state_manager=object(),
            audit_logger=object(),
            observer=object(),
            invoker=object(),
            artifact_store=object(),
            workflow_service=object(),
            memory_sink=None,
        ),
    )

    workflow_description = registry.get("RunDsimEngineeringWorkflow").get_schema().description
    assert "Preferred" in workflow_description
    assert "permissions" in workflow_description
    assert "artifacts" in workflow_description

    for name in [
        "SaveProjectContext",
        "GenerateDsimReport",
        "DiagnoseSimulationFailure",
        "CompareSimulationRuns",
        "RunParameterSweep",
    ]:
        description = registry.get(name).get_schema().description
        assert "RunDsimEngineeringWorkflow" in description
