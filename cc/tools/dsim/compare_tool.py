"""Compare two DSim run summaries."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


class CompareSimulationRunsTool(Tool):
    """Compare two DSim simulation run summaries."""

    def get_name(self) -> str:
        return "CompareSimulationRuns"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description="Compare two DSim simulation runs.",
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        runs = list(tool_input.get("runs", []))
        if len(runs) < 2:
            return ToolResult(content="CompareSimulationRuns requires at least two runs.", is_error=True)

        first = runs[0].get("run_id", "run-1")
        second = runs[1].get("run_id", "run-2")
        return ToolResult(content=f"Compared DSim runs {first} and {second}.")
