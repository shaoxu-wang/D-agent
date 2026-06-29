"""Runtime-only DSim project memory context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class MemoryCandidateReader(Protocol):
    def list_confirmed_memory_candidates(self, project_id: str) -> list[dict[str, Any]]:
        """Return confirmed project memory candidates."""


@dataclass(frozen=True, slots=True)
class MemoryContextItem:
    memory_id: str
    kind: str
    content: str
    applies_to: list[str]
    evidence_refs: list[dict[str, Any]]
    priority: int = 0
    created_at: str = ""

    def compact(self) -> dict[str, Any]:
        preview = self.content if len(self.content) <= 120 else f"{self.content[:117]}..."
        return {
            "memory_id": self.memory_id,
            "kind": self.kind,
            "content_preview": preview,
            "applies_to": self.applies_to,
            "evidence_refs": self.evidence_refs,
            "priority": self.priority,
        }


@dataclass(frozen=True, slots=True)
class MemoryContext:
    project_id: str
    applies_to: str
    memories: list[MemoryContextItem]
    warnings: list[str]

    def compact(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "applies_to": self.applies_to,
            "memories": [item.compact() for item in self.memories],
            "warnings": self.warnings,
        }


class MemoryContextBuilder:
    """Build runtime memory context from confirmed project memory."""

    def __init__(self, *, reader: MemoryCandidateReader, max_items: int = 5) -> None:
        self._reader = reader
        self._max_items = max_items

    def build(self, *, project_id: str, applies_to: str) -> MemoryContext:
        candidates = self._reader.list_confirmed_memory_candidates(project_id)
        items = [self._item_from_candidate(candidate) for candidate in candidates]
        relevant = [
            item
            for item in items
            if not item.applies_to or applies_to in item.applies_to or "*" in item.applies_to
        ]
        relevant.sort(key=lambda item: (-item.priority, item.created_at, item.memory_id))
        warnings = [] if relevant else [f"No confirmed project memory found for {project_id}."]
        return MemoryContext(
            project_id=project_id,
            applies_to=applies_to,
            memories=relevant[: self._max_items],
            warnings=warnings,
        )

    def _item_from_candidate(self, candidate: dict[str, Any]) -> MemoryContextItem:
        return MemoryContextItem(
            memory_id=str(candidate.get("memory_id") or ""),
            kind=str(candidate.get("kind") or "project_fact"),
            content=str(candidate.get("content") or ""),
            applies_to=[str(item) for item in candidate.get("applies_to", [])],
            evidence_refs=list(candidate.get("evidence_refs", [])),
            priority=int(candidate.get("priority") or 0),
            created_at=str(candidate.get("created_at") or ""),
        )
