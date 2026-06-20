"""Dynamic registration for Agent-side DSim tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cc.tools.dsim.compare_tool import CompareSimulationRunsTool
from cc.tools.dsim.diagnose_tool import DiagnoseSimulationFailureTool
from cc.tools.dsim.report_tool import GenerateDsimReportTool
from cc.tools.dsim.save_context_tool import SaveProjectContextTool
from cc.tools.dsim.sweep_tool import RunParameterSweepTool

if TYPE_CHECKING:
    from cc.tools.base import ToolRegistry


def has_dsim_mcp_capability(registry: ToolRegistry) -> bool:
    """Return whether the MCP DSim service appears to be registered."""
    return (
        registry.get("mcp__dsim__ValidateDsimEnvironment") is not None
        or registry.get("mcp__dsim__OpenDsimProject") is not None
    )


def register_dsim_tools(registry: ToolRegistry, *, invoker: object | None = None) -> None:
    """Register Agent-side DSim tools when DSim MCP capabilities are present."""
    if not has_dsim_mcp_capability(registry):
        return

    for tool in [
        SaveProjectContextTool(),
        GenerateDsimReportTool(),
        DiagnoseSimulationFailureTool(),
        CompareSimulationRunsTool(),
        RunParameterSweepTool(invoker=invoker),
    ]:
        if registry.get(tool.get_name()) is None:
            registry.register(tool)
