"""Tests for StreamingToolExecutor.

Verifies T10.5: Tools start executing before stream completes.
"""

import asyncio
import time
from typing import Any

from cc.models.content_blocks import ToolUseBlock
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema
from cc.tools.streaming_executor import StreamingToolExecutor


class SlowTool(Tool):
    def __init__(self, delay: float = 0.1) -> None:
        self._delay = delay

    def get_name(self) -> str:
        return "slow"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name="slow", description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        await asyncio.sleep(self._delay)
        return ToolResult(content=f"done after {self._delay}s")

    def is_concurrency_safe(self, tool_input: dict[str, Any]) -> bool:
        return True  # P1a: enable parallel execution for this test tool


class FakePermissionRecord:
    allowed = True
    decision = "allow"


class RecordingPermissionChecker:
    def __init__(self) -> None:
        self.calls = []

    async def check_with_record(self, tool_name: str, tool_input: dict[str, Any], *, tool_call_id: str):
        self.calls.append((tool_call_id, tool_name, tool_input))
        return FakePermissionRecord()


class RecordingObserver:
    def __init__(self) -> None:
        self.calls = []

    def observe(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


class TestStreamingToolExecutor:
    async def test_tools_start_immediately(self) -> None:
        """tool_1 starts executing while tool_2 hasn't been added yet."""
        reg = ToolRegistry()
        reg.register(SlowTool(delay=0.1))

        executor = StreamingToolExecutor(reg)

        # Add first tool — it starts executing immediately
        start = time.monotonic()
        executor.add_tool(ToolUseBlock(id="t1", name="slow", input={}))

        # Simulate API still streaming (wait a bit)
        await asyncio.sleep(0.05)

        # Add second tool
        executor.add_tool(ToolUseBlock(id="t2", name="slow", input={}))

        # Get all results
        results = await executor.get_results()
        elapsed = time.monotonic() - start

        assert len(results) == 2
        assert results[0][0] == "t1"
        assert results[1][0] == "t2"
        # t1 started 0.05s before t2, so total should be ~0.15s not ~0.2s
        assert elapsed < 0.2

    async def test_results_in_order(self) -> None:
        """Results returned in insertion order regardless of completion order."""
        reg = ToolRegistry()
        reg.register(SlowTool(delay=0.05))

        executor = StreamingToolExecutor(reg)
        executor.add_tool(ToolUseBlock(id="first", name="slow", input={}))
        executor.add_tool(ToolUseBlock(id="second", name="slow", input={}))

        results = await executor.get_results()
        assert results[0][0] == "first"
        assert results[1][0] == "second"

    async def test_unknown_tool(self) -> None:
        reg = ToolRegistry()
        executor = StreamingToolExecutor(reg)
        executor.add_tool(ToolUseBlock(id="t1", name="unknown", input={}))

        results = await executor.get_results()
        assert results[0][1].is_error

    async def test_has_pending(self) -> None:
        reg = ToolRegistry()
        reg.register(SlowTool())
        executor = StreamingToolExecutor(reg)
        assert not executor.has_pending

        executor.add_tool(ToolUseBlock(id="t1", name="slow", input={}))
        assert executor.has_pending

    async def test_observer_receives_permission_record_after_execution(self) -> None:
        reg = ToolRegistry()
        reg.register(SlowTool(delay=0))
        checker = RecordingPermissionChecker()
        observer = RecordingObserver()
        executor = StreamingToolExecutor(
            reg,
            permission_checker=checker,
            result_observers=[observer],
        )

        executor.add_tool(ToolUseBlock(id="toolu_1", name="slow", input={"value": 1}))
        results = await executor.get_results()

        assert results[0][1].content == "done after 0s"
        assert checker.calls == [("toolu_1", "slow", {"value": 1})]
        assert observer.calls[0]["tool_call_id"] == "toolu_1"
        assert observer.calls[0]["permission_record"].decision == "allow"
        assert observer.calls[0]["duration_ms"] >= 0
