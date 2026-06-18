"""DSim MCP tool invoker for Agent-side DSim tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from cc.tools.base import ToolRegistry, ToolResult

PermissionChecker = Callable[[str, dict[str, Any]], Awaitable[bool]]


class DsimToolInvoker:
    """Invoke registered DSim MCP tools with optional permission checks."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        permission_checker: PermissionChecker | None = None,
    ) -> None:
        self._registry = registry
        self._permission_checker = permission_checker

    async def call(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Invoke a DSim MCP tool by registry name."""
        tool = self._registry.get(tool_name)
        if tool is None:
            return ToolResult(content=f"DSim MCP tool not found: {tool_name}", is_error=True)

        if self._permission_checker is not None:
            allowed = await self._permission_checker(tool_name, tool_input)
            if not allowed:
                return ToolResult(content="Denied by permission policy", is_error=True)

        return await tool.execute(tool_input)
