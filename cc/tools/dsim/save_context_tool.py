"""Save DSim project context."""

from __future__ import annotations

from typing import Any

from cc.dsim.memory_kinds import STAGE2C_MEMORY_KINDS
from cc.tools.base import Tool, ToolResult, ToolSchema
from cc.tools.dsim.result_helpers import workflow_tool_result


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
            input_schema={
                "type": "object",
                "required": ["project_id", "kind", "content"],
                "properties": {
                    "project_id": {"type": "string"},
                    "project_path": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": sorted(STAGE2C_MEMORY_KINDS),
                        "description": "Stage 2C DSim project memory category.",
                    },
                    "content": {"type": "string"},
                    "applies_to": {"type": "array", "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "items": {"type": "object"}},
                    "confirmed": {"type": "boolean"},
                    "priority": {"type": "integer"},
                    "interpretive": {"type": "boolean"},
                },
            },
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        kind = str(tool_input.get("kind", "project_fact"))
        if kind not in STAGE2C_MEMORY_KINDS:
            return ToolResult(
                content=(
                    f"Unsupported DSim memory kind: {kind}. "
                    f"Supported kinds: {', '.join(sorted(STAGE2C_MEMORY_KINDS))}."
                ),
                is_error=True,
            )
        requires_confirmation = kind != "project_fact" or bool(tool_input.get("interpretive"))
        if requires_confirmation and not tool_input.get("confirmed"):
            return ToolResult(
                content="Confirmation is required before saving interpretive or preference-like DSim project memory.",
                is_error=True,
            )
        if self._workflow_service is None or not hasattr(self._workflow_service, "save_project_context"):
            return ToolResult(content="DSim workflow service is required for SaveProjectContext.", is_error=True)
        result = await self._workflow_service.save_project_context(tool_input)
        project_id = getattr(result, "project_id", None) or tool_input.get("project_id") or "unknown-project"
        return workflow_tool_result(
            result,
            success_content=f"DSim project context saved for {project_id}.",
            failure_prefix=f"DSim project context save for {project_id}",
        )
