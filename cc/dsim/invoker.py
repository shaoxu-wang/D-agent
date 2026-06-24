"""DSim MCP tool invoker for Agent-side DSim tools."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol

from cc.tools.base import ToolRegistry, ToolResult

if TYPE_CHECKING:
    from collections.abc import Callable

    from cc.permissions.gate import PermissionDecisionRecord


class PermissionChecker(Protocol):
    async def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        *,
        tool_call_id: str,
    ) -> PermissionDecisionRecord:
        ...


class DsimToolInvoker:
    """Invoke registered DSim MCP tools with optional permission checks."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        observer: Any | None = None,
        permission_checker: PermissionChecker | None = None,
        tool_call_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._registry = registry
        self._observer = observer
        self._permission_checker = permission_checker
        self._tool_call_id_factory = tool_call_id_factory or self._default_tool_call_id

    async def call(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Invoke a DSim MCP tool by registry name."""
        tool_call_id = self._tool_call_id_factory()
        tool = self._registry.get(tool_name)
        if tool is None:
            return ToolResult(content=f"DSim MCP tool not found: {tool_name}", is_error=True)

        permission_record: PermissionDecisionRecord | None = None
        if self._permission_checker is not None:
            permission_record = await self._permission_checker(tool_name, tool_input, tool_call_id=tool_call_id)
            if not permission_record.allowed:
                return ToolResult(content="Denied by permission policy", is_error=True)

        started = time.perf_counter()
        result = await tool.execute(tool_input)
        duration_ms = int((time.perf_counter() - started) * 1000)

        if self._observer is not None and tool_name.startswith("mcp__dsim__"):
            self._observer.observe(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_input=tool_input,
                result=result,
                permission_record=permission_record,
                duration_ms=duration_ms,
            )

        return result

    def _default_tool_call_id(self) -> str:
        return f"toolu_{int(time.time() * 1000)}"
