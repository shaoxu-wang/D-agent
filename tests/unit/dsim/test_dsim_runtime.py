import shutil
from pathlib import Path

import pytest

from cc.dsim.runtime import DsimRuntimeBundle, build_dsim_runtime
from cc.permissions.gate import PermissionDecisionRecord
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


def test_runtime_bundle_carries_dependencies() -> None:
    registry = object()
    permission_ctx = object()
    bundle = DsimRuntimeBundle(
        registry=registry,
        permission_ctx=permission_ctx,
        state_manager=object(),
        audit_logger=object(),
        observer=object(),
        invoker=object(),
        artifact_store=object(),
        workflow_service=object(),
        memory_sink=None,
    )

    assert bundle.registry is registry
    assert bundle.permission_ctx is permission_ctx
    assert bundle.state_manager is not None
    assert bundle.audit_logger is not None
    assert bundle.observer is not None
    assert bundle.invoker is not None
    assert bundle.artifact_store is not None
    assert bundle.workflow_service is not None
    assert bundle.memory_sink is None


class FakePermissionContext:
    async def check_with_record(
        self,
        tool_name: str,
        tool_input: dict[str, object],
        *,
        tool_call_id: str = "",
    ) -> PermissionDecisionRecord:
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


class FakeDsimTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__ValidateDsimEnvironment"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(
            content="ok",
            metadata={"structured": {"ok": True, "service": "dsim", "tool": "ValidateDsimEnvironment"}},
        )


@pytest.mark.asyncio
async def test_runtime_invoker_uses_permission_decision_records() -> None:
    workspace = Path(".test_dsim_runtime")
    if workspace.exists():
        shutil.rmtree(workspace)
    registry = ToolRegistry()
    registry.register(FakeDsimTool())

    try:
        bundle = build_dsim_runtime(
            workspace=str(workspace),
            session_id="session-1",
            permission_ctx=FakePermissionContext(),
            registry=registry,
        )
        result = await bundle.invoker.call("mcp__dsim__ValidateDsimEnvironment", {})

        assert result.is_error is False
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)
