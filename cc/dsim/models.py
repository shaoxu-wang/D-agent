"""Pydantic models for DSim Agent state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


class VersionedModel(BaseModel):
    """Base model for local DSim state files."""

    schema_version: int = 1
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class DsimProject(VersionedModel):
    """Persisted DSim project state."""

    project_id: str
    project_path: str
    schematic_path: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    run_summaries: list[dict[str, Any]] = Field(default_factory=list)
    curve_summaries: list[dict[str, Any]] = Field(default_factory=list)
    workflow_summaries: list[dict[str, Any]] = Field(default_factory=list)
    sweep_summaries: list[dict[str, Any]] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = Field(default_factory=list)


class ActiveDsimContext(VersionedModel):
    """Session-level active DSim context."""

    session_id: str
    client_id: str = "local"
    active_project_id: str | None = None
    active_handle_id: str | None = None
    active_run_id: str | None = None
