"""Save DSim project context."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


class SaveProjectContextTool(Tool):
    """Save confirmed DSim project context."""

    def __init__(self, workflow_service: Any | None = None) -> None:
        self._workflow_service = workflow_service

    def get_name(self) -> str:
        return "SaveProjectContext"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description=(
                "Save confirmed DSim project context and memory candidates. "
                "For multi-step work prefer RunDsimEngineeringWorkflow."
            ),
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        if tool_input.get("kind") in {"conclusion", "preference", "recommendation"} and not tool_input.get("confirmed"):
            return ToolResult(
                content="Confirmation is required before saving interpretive DSim context.",
                is_error=True,
            )
        if self._workflow_service is None or not hasattr(self._workflow_service, "save_project_context"):
            return ToolResult(content="DSim workflow service is required for SaveProjectContext.", is_error=True)
        result = await self._workflow_service.save_project_context(tool_input)
        structured = result.model_dump() if hasattr(result, "model_dump") else result
        project_id = getattr(result, "project_id", None) or tool_input.get("project_id") or "unknown-project"
        return ToolResult(
            content=f"DSim project context saved for {project_id}.",
            metadata={"structured": structured},
        )
