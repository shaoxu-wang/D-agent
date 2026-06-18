"""Pure conversion for structured DSim MCP results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdaptedDsimResult:
    """State-oriented view of a structured DSim tool result."""

    state_events: list[dict[str, Any]] = field(default_factory=list)
    result_summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class DsimResultAdapter:
    """Convert structured DSim MCP payloads into state and audit data."""

    def adapt(self, payload: dict[str, Any]) -> AdaptedDsimResult:
        """Adapt a unified DSim MCP response payload."""
        return AdaptedDsimResult(
            state_events=list(payload.get("state_updates", [])),
            artifacts=list(payload.get("artifacts", [])),
            result_summary={
                "ok": payload.get("ok"),
                "tool": payload.get("tool"),
                "error": payload.get("error"),
            },
        )
