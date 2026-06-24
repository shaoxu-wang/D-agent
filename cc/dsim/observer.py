"""Internal observer for DSim MCP tool results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.result_adapter import DsimResultAdapter

if TYPE_CHECKING:
    from cc.tools.base import ToolResult


class DsimToolResultObserver:
    """Apply structured DSim tool outputs to state and audit sinks."""

    def __init__(self, *, state_manager: Any, audit_logger: Any) -> None:
        self._state_manager = state_manager
        self._audit_logger = audit_logger
        self._adapter = DsimResultAdapter()

    def observe(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        result: ToolResult,
        permission_record: Any,
        duration_ms: int,
    ) -> None:
        """Observe one completed tool call if it is a structured DSim result."""
        if not tool_name.startswith("mcp__dsim__"):
            return

        payload = result.metadata.get("structured")
        if not isinstance(payload, dict) or payload.get("service") != "dsim":
            return

        adapted = self._adapter.adapt(payload)
        self._state_manager.apply_state_events(adapted.state_events)
        for artifact in adapted.artifacts:
            if hasattr(self._state_manager, "add_artifact_ref"):
                runtime = payload.get("runtime", {})
                project_id = runtime.get("project_id", runtime.get("handle_id", "unknown-project"))
                self._state_manager.add_artifact_ref(
                    project_id=str(project_id),
                    artifact_ref=artifact,
                )
        self._audit_logger.write_entry(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "input_summary": str(tool_input)[:200],
                "result_summary": adapted.result_summary,
                "ok": bool(payload.get("ok")),
                "error": payload.get("error"),
                "permission_decision": getattr(permission_record, "decision", None),
                "risk_level": getattr(permission_record, "risk_level", None),
                "duration_ms": duration_ms,
            }
        )
