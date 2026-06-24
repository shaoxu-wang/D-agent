"""High-level DSim engineering workflow tool."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from cc.dsim.workflow_models import DsimWorkflowMode, DsimWorkflowRequest
from cc.tools.base import Tool, ToolResult, ToolSchema


class RunDsimEngineeringWorkflowTool(Tool):
    """Run a high-level DSim engineering workflow through DsimWorkflowService."""

    def __init__(self, workflow_service: Any) -> None:
        self._workflow_service = workflow_service

    def get_name(self) -> str:
        return "RunDsimEngineeringWorkflow"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description=(
                "Preferred DSim entrypoint for multi-step engineering workflows. "
                "Use it for inspection, one simulation run, diagnosis, report generation, or a conservative sweep. "
                "It routes lower-level MCP calls through permissions, state, audit, and artifacts."
            ),
            input_schema={
                "type": "object",
                "required": ["mode"],
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [mode.value for mode in DsimWorkflowMode],
                        "description": "Workflow mode to run. Must be selected explicitly.",
                    },
                    "project_id": {"type": "string"},
                    "project_path": {"type": "string"},
                    "handle_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "config": {"type": "object"},
                    "parameters": {"type": "array", "items": {"type": "object"}},
                    "combinations": {"type": "array", "items": {"type": "object"}},
                    "runs": {"type": "array", "items": {"type": "object"}},
                    "timeout_seconds": {"type": "integer", "minimum": 1},
                    "status": {"type": "string"},
                    "error": {"type": "object"},
                    "confirmed": {"type": "boolean"},
                },
            },
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        try:
            request = DsimWorkflowRequest(**tool_input)
        except ValidationError as exc:
            return ToolResult(content=f"Invalid DSim workflow request: {exc}", is_error=True)

        result = await self._workflow_service.run(request)
        return ToolResult(content=str(result))
