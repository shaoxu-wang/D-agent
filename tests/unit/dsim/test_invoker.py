import pytest

from cc.dsim.invoker import DsimToolInvoker
from cc.permissions.gate import PermissionDecisionRecord
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(
            content="opened",
            metadata={"structured": {"ok": True, "service": "dsim", "tool": "OpenDsimProject"}},
        )


class FakeErrorTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__RunDsimSimulation"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(
            content="failed",
            is_error=True,
            metadata={"structured": {"ok": False, "service": "dsim", "tool": "RunDsimSimulation"}},
        )


class RecordingObserver:
    def __init__(self) -> None:
        self.calls = []

    def observe(self, **kwargs):
        self.calls.append(kwargs)


def _allowed_record(tool_call_id: str, tool_name: str) -> PermissionDecisionRecord:
    return PermissionDecisionRecord(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        decision="allow",
        source="test",
        allowed=True,
        input_hash="hash",
        input_summary="summary",
        created_at="2026-01-01T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_invoker_uses_permission_checker_and_registry() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool())
    calls = []
    observer = RecordingObserver()

    async def permission_checker(tool_name: str, tool_input: dict, *, tool_call_id: str) -> PermissionDecisionRecord:
        calls.append((tool_name, tool_input, tool_call_id))
        return _allowed_record(tool_call_id, tool_name)

    invoker = DsimToolInvoker(
        registry=registry,
        permission_checker=permission_checker,
        observer=observer,
        tool_call_id_factory=lambda: "toolu_test",
    )
    result = await invoker.call("mcp__dsim__OpenDsimProject", {"path": "demo.dsim"})

    assert result.content == "opened"
    assert calls == [("mcp__dsim__OpenDsimProject", {"path": "demo.dsim"}, "toolu_test")]
    assert len(observer.calls) == 1
    assert observer.calls[0]["tool_call_id"] == "toolu_test"
    assert observer.calls[0]["permission_record"].allowed is True
    assert observer.calls[0]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_invoker_denied_call_skips_observer() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool())
    observer = RecordingObserver()

    async def permission_checker(tool_name: str, tool_input: dict, *, tool_call_id: str) -> PermissionDecisionRecord:
        return PermissionDecisionRecord(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            decision="deny",
            source="test",
            allowed=False,
            input_hash="hash",
            input_summary="summary",
            created_at="2026-01-01T00:00:00+00:00",
        )

    invoker = DsimToolInvoker(
        registry=registry,
        permission_checker=permission_checker,
        observer=observer,
        tool_call_id_factory=lambda: "toolu_deny",
    )
    result = await invoker.call("mcp__dsim__OpenDsimProject", {"path": "demo.dsim"})

    assert result.is_error is True
    assert observer.calls == []


@pytest.mark.asyncio
async def test_invoker_observes_structured_error_result() -> None:
    registry = ToolRegistry()
    registry.register(FakeErrorTool())
    observer = RecordingObserver()

    async def permission_checker(tool_name: str, tool_input: dict, *, tool_call_id: str) -> PermissionDecisionRecord:
        return _allowed_record(tool_call_id, tool_name)

    invoker = DsimToolInvoker(
        registry=registry,
        permission_checker=permission_checker,
        observer=observer,
        tool_call_id_factory=lambda: "toolu_error",
    )
    result = await invoker.call("mcp__dsim__RunDsimSimulation", {"handle_id": "h1"})

    assert result.is_error is True
    assert len(observer.calls) == 1
    assert observer.calls[0]["result"].is_error is True
