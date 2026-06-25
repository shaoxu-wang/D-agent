"""Generate a concise DSim report from local summaries."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema
from cc.tools.dsim.result_helpers import workflow_tool_result


class GenerateDsimReportTool(Tool):
    """Generate a concise report from provided DSim summaries."""

    def __init__(self, workflow_service: Any | None = None) -> None:
        self._workflow_service = workflow_service

    def get_name(self) -> str:
        return "GenerateDsimReport"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description=(
                "Generate a DSim report artifact from existing summaries. "
                "For multi-step work prefer RunDsimEngineeringWorkflow."
            ),
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        if self._workflow_service is None or not hasattr(self._workflow_service, "generate_report"):
            return ToolResult(content="DSim workflow service is required for GenerateDsimReport.", is_error=True)
        result = await self._workflow_service.generate_report(tool_input)
        project_id = getattr(result, "project_id", None) or tool_input.get("project_id") or "unknown-project"
        return workflow_tool_result(
            result,
            success_content=f"DSim report generated for {project_id}.",
            failure_prefix=f"DSim report for {project_id}",
        )
