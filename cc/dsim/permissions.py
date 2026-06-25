"""DSim-specific permission risk classification."""

from __future__ import annotations

from typing import Literal

DsimRisk = Literal["allow", "ask", "strong_ask"]


class DsimRiskClassifier:
    """Classify DSim MCP and agent-side tool calls by execution risk."""

    AGENT_TOOL_NAMES = frozenset({
        "RunDsimEngineeringWorkflow",
        "SaveProjectContext",
        "GenerateDsimReport",
        "DiagnoseSimulationFailure",
        "CompareSimulationRuns",
        "RunParameterSweep",
    })
    MCP_ALIAS_NAMES = frozenset({
        "OpenDsimProject",
        "ListDsimCurves",
        "ReadDsimCurves",
        "RunDsimSimulation",
    })
    EXECUTION_AGENT_TOOLS = frozenset({
        "RunDsimEngineeringWorkflow",
        "GenerateDsimReport",
        "DiagnoseSimulationFailure",
        "CompareSimulationRuns",
        "RunParameterSweep",
    })
    STRONG_ASK_KEYWORDS = ("Delete", "SaveSchematicFile", "Write", "Export")
    RAW_DATA_TOOLS = frozenset({
        "mcp__dsim__GetAllCurveData",
        "mcp__dsim__GetCurveData",
    })

    def is_dsim_tool(self, tool_name: str) -> bool:
        """Return whether the tool belongs to the DSim integration boundary."""
        return (
            tool_name.startswith("mcp__dsim__")
            or tool_name in self.AGENT_TOOL_NAMES
            or tool_name in self.MCP_ALIAS_NAMES
        )

    def classify(self, tool_name: str, tool_input: dict[str, object] | None = None) -> DsimRisk:
        """Return the required permission level for a DSim tool call."""
        if not self.is_dsim_tool(tool_name):
            return "allow"

        if any(keyword in tool_name for keyword in self.STRONG_ASK_KEYWORDS):
            return "strong_ask"

        if tool_name in self.RAW_DATA_TOOLS:
            return "ask"

        if tool_name in self.EXECUTION_AGENT_TOOLS:
            return "ask"

        if tool_name == "ReadDsimCurves":
            mode = str((tool_input or {}).get("mode", "summary")).lower()
            if mode != "summary":
                return "ask"
            return "allow"

        if tool_name.endswith("RunDsimSimulation") or tool_name == "RunDsimSimulation":
            return "ask"

        return "allow"
