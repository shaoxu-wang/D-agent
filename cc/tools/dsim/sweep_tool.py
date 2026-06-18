"""Run a conservative serial DSim parameter sweep."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


class RunParameterSweepTool(Tool):
    """Prepare or run a conservative serial DSim parameter sweep."""

    def __init__(self, invoker: Any) -> None:
        self._invoker = invoker

    def get_name(self) -> str:
        return "RunParameterSweep"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description="Run a serial DSim parameter sweep.",
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        combinations = list(tool_input.get("combinations", []))
        if len(combinations) > 20 and not tool_input.get("confirmed"):
            return ToolResult(
                content="RunParameterSweep supports at most 20 combinations without explicit confirmation.",
                is_error=True,
            )
        return ToolResult(content=f"Prepared serial DSim sweep with {len(combinations)} combinations.")
