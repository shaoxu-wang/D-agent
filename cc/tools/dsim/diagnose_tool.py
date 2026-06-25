"""Diagnose a mock DSim simulation failure."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema
from cc.tools.dsim.result_helpers import workflow_tool_result


class DiagnoseSimulationFailureTool(Tool):
    """Summarize a DSim simulation failure reason."""

    def __init__(self, workflow_service: Any | None = None) -> None:
        self._workflow_service = workflow_service

    def get_name(self) -> str:
        return "DiagnoseSimulationFailure"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description=(
                "Diagnose an existing DSim simulation failure from stored or provided evidence. "
                "For multi-step work prefer RunDsimEngineeringWorkflow."
            ),
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        if self._workflow_service is None or not hasattr(self._workflow_service, "diagnose_existing"):
            return ToolResult(content="DSim workflow service is required for DiagnoseSimulationFailure.", is_error=True)
        result = await self._workflow_service.diagnose_existing(tool_input)
        run_id = getattr(result, "run_id", None) or tool_input.get("run_id") or "unknown-run"
        return workflow_tool_result(
            result,
            success_content=f"DSim diagnosis completed for {run_id}.",
            failure_prefix=f"DSim diagnosis for {run_id}",
        )
