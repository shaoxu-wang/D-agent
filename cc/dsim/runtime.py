"""Runtime bundle for DSim Agent-side workflow wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from cc.dsim.artifacts import DsimArtifactStore
from cc.dsim.audit import DsimAuditLogger
from cc.dsim.invoker import DsimToolInvoker
from cc.dsim.memory_sink import DeferredMemorySink
from cc.dsim.observer import DsimToolResultObserver
from cc.dsim.state import DsimProjectStateManager
from cc.permissions.gate import PermissionDecisionRecord

if TYPE_CHECKING:
    from cc.tools.base import ToolRegistry


@dataclass(slots=True)
class DsimRuntimeBundle:
    """Container for runtime dependencies used by DSim agent tools."""

    registry: ToolRegistry
    permission_ctx: Any
    state_manager: DsimProjectStateManager
    audit_logger: DsimAuditLogger
    observer: DsimToolResultObserver
    invoker: DsimToolInvoker
    artifact_store: DsimArtifactStore
    workflow_service: Any
    memory_sink: Any | None = None


def build_dsim_runtime(
    *,
    workspace: str,
    session_id: str,
    permission_ctx: Any,
    registry: ToolRegistry,
    client_id: str = "local",
) -> DsimRuntimeBundle:
    """Build a DSim runtime bundle from already connected MCP capabilities."""
    state_manager = DsimProjectStateManager(workspace=workspace, session_id=session_id, client_id=client_id)
    audit_logger = DsimAuditLogger(workspace=workspace)
    observer = DsimToolResultObserver(state_manager=state_manager, audit_logger=audit_logger)

    async def _check(
        tool_name: str,
        tool_input: dict[str, Any],
        *,
        tool_call_id: str,
    ) -> PermissionDecisionRecord:
        if permission_ctx is not None and hasattr(permission_ctx, "check_with_record"):
            record = await permission_ctx.check_with_record(
                tool_name,
                tool_input,
                tool_call_id=tool_call_id,
            )
            return cast("PermissionDecisionRecord", record)
        allowed = True
        if permission_ctx is not None and hasattr(permission_ctx, "check"):
            allowed = await permission_ctx.check(tool_name, tool_input)
        return PermissionDecisionRecord(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            decision="allow" if allowed else "deny",
            source="legacy_permission_check",
            allowed=bool(allowed),
            input_hash="",
            input_summary=str(tool_input)[:200],
        )

    invoker = DsimToolInvoker(
        registry=registry,
        observer=observer,
        permission_checker=_check if permission_ctx is not None else None,
    )
    artifact_store = DsimArtifactStore(workspace=workspace)
    memory_sink = DeferredMemorySink(state_manager=state_manager)
    bundle = DsimRuntimeBundle(
        registry=registry,
        permission_ctx=permission_ctx,
        state_manager=state_manager,
        audit_logger=audit_logger,
        observer=observer,
        invoker=invoker,
        artifact_store=artifact_store,
        workflow_service=None,
        memory_sink=memory_sink,
    )
    from cc.dsim.workflow import DsimWorkflowService

    bundle.workflow_service = DsimWorkflowService(runtime=bundle)
    return bundle
