"""Diagnose a mock DSim simulation failure."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


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
        if self._workflow_service is None:
            run_id = tool_input.get("run_id", "unknown-run")
            error = tool_input.get("error") or {}
            code = error.get("code", "UNKNOWN_FAILURE")
            return ToolResult(content=f"Diagnosis for {run_id}: failure code {code}.")
        result = await self._workflow_service.diagnose_existing(tool_input)
        return ToolResult(content=str(result))
