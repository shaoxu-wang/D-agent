"""Deferred memory sink for DSim workflow candidates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cc.dsim.state import DsimProjectStateManager


class DeferredMemorySink:
    """Store confirmed DSim memory candidates locally for later review."""

    def __init__(self, *, state_manager: DsimProjectStateManager) -> None:
        self._state_manager = state_manager

    def save_confirmed(self, *, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Record a confirmed candidate without writing global long-term memory."""
        project_id = str(context["project_id"])
        payload = {**candidate, "long_term_memory_status": "deferred"}
        self._state_manager.record_memory_candidate(project_id=project_id, candidate=payload)
        return payload
