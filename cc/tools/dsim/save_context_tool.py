"""Save DSim project context."""

from __future__ import annotations

from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema


class SaveProjectContextTool(Tool):
    """Save confirmed DSim project context."""

    def get_name(self) -> str:
        return "SaveProjectContext"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.get_name(),
            description="Save confirmed DSim project context.",
            input_schema={"type": "object"},
        )

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        if tool_input.get("kind") in {"conclusion", "preference", "recommendation"} and not tool_input.get("confirmed"):
            return ToolResult(
                content="Confirmation is required before saving interpretive DSim context.",
                is_error=True,
            )
        return ToolResult(content="DSim project context saved.")
