"""Run a conservative serial DSim parameter sweep."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


class RunParameterSweepTool(Tool):
    """Prepare or run a conservative serial DSim parameter sweep."""

    def __init__(self, workflow_service: Any | None = None) -> None:
        self._workflow_service = workflow_service

    def get_name(self) -> str:
        return "RunParameterSweep"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description=(
                "Run a conservative serial DSim parameter sweep and write a sweep artifact. "
                "For multi-step work prefer RunDsimEngineeringWorkflow."
            ),
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        combinations = list(tool_input.get("combinations", []))
        if len(combinations) > 20 and not tool_input.get("confirmed"):
            return ToolResult(
                content="RunParameterSweep supports at most 20 combinations without explicit confirmation.",
                is_error=True,
            )
        if self._workflow_service is None:
            return ToolResult(content=f"Prepared serial DSim sweep with {len(combinations)} combinations.")
        result = await self._workflow_service.run_sweep(tool_input)
        return ToolResult(content=str(result))
