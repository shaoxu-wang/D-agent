from cc.dsim.registry import has_dsim_mcp_capability, register_dsim_tools
from cc.dsim.runtime import DsimRuntimeBundle
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeDsimMcpTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(content="ok")


def _fake_tool_class(name: str, log: dict[str, dict]) -> type[Tool]:
    class _FakeTool(Tool):
        def __init__(self, **kwargs) -> None:
            log[name] = kwargs

        def get_name(self) -> str:
            return name

        def get_schema(self) -> ToolSchema:
            return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

        async def execute(self, tool_input: dict) -> ToolResult:
            return ToolResult(content="ok")

    return _FakeTool


def test_register_dsim_tools_requires_mcp_capability() -> None:
    registry = ToolRegistry()

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

    assert has_dsim_mcp_capability(registry) is False
    assert registry.get("RunParameterSweep") is None


def test_register_dsim_tools_when_dsim_mcp_exists() -> None:
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

    assert has_dsim_mcp_capability(registry) is True
    assert registry.get("SaveProjectContext") is not None
    assert registry.get("RunDsimEngineeringWorkflow") is not None
    assert registry.get("RunParameterSweep") is not None


def test_register_dsim_tools_injects_runtime_service() -> None:
    registry = ToolRegistry()
    registry.register(FakeDsimMcpTool())
    runtime = DsimRuntimeBundle(
        registry=registry,
        permission_ctx=object(),
        state_manager=object(),
        audit_logger=object(),
        observer=object(),
        invoker=object(),
        artifact_store=object(),
        workflow_service=object(),
        memory_sink=None,
    )
    init_log: dict[str, dict] = {}

    import cc.dsim.registry as mod

    mod.SaveProjectContextTool = _fake_tool_class("SaveProjectContext", init_log)
    mod.GenerateDsimReportTool = _fake_tool_class("GenerateDsimReport", init_log)
    mod.DiagnoseSimulationFailureTool = _fake_tool_class("DiagnoseSimulationFailure", init_log)
    mod.CompareSimulationRunsTool = _fake_tool_class("CompareSimulationRuns", init_log)
    mod.RunParameterSweepTool = _fake_tool_class("RunParameterSweep", init_log)
    mod.RunDsimEngineeringWorkflowTool = _fake_tool_class("RunDsimEngineeringWorkflow", init_log)

    register_dsim_tools(registry, runtime=runtime)

    assert init_log["RunDsimEngineeringWorkflow"]["workflow_service"] is runtime.workflow_service
    assert init_log["SaveProjectContext"]["workflow_service"] is runtime.workflow_service
    assert init_log["GenerateDsimReport"]["workflow_service"] is runtime.workflow_service
    assert init_log["DiagnoseSimulationFailure"]["workflow_service"] is runtime.workflow_service
    assert init_log["CompareSimulationRuns"]["workflow_service"] is runtime.workflow_service
    assert init_log["RunParameterSweep"]["workflow_service"] is runtime.workflow_service
