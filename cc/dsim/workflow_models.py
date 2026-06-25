"""Workflow data models for Stage 2A DSim orchestration."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DsimWorkflowMode(StrEnum):
    inspect_only = "inspect_only"
    single_run = "single_run"
    diagnose_existing = "diagnose_existing"
    report_existing = "report_existing"
    sweep = "sweep"


class DsimArtifactRef(BaseModel):
    artifact_id: str
    kind: str
    path: str
    storage_key: str
    uri: str | None = None
    mime_type: str


class DsimMemoryCandidate(BaseModel):
    kind: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    confirmed: bool = False


class DsimWorkflowRequest(BaseModel):
    mode: DsimWorkflowMode
    project_id: str | None = None
    project_path: str | None = None
    handle_id: str | None = None
    run_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    combinations: list[dict[str, Any]] = Field(default_factory=list)
    runs: list[dict[str, Any]] = Field(default_factory=list)
    timeout_seconds: int | None = None
    status: str | None = None
    error: dict[str, Any] | None = None
    confirmed: bool = False


class DsimWorkflowStep(BaseModel):
    name: str
    status: str
    tool_name: str | None = None
    input_summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    suggested_recovery: str | None = None
    state_written: bool = False
    artifact_written: bool = False


class DsimWorkflowResult(BaseModel):
    mode: DsimWorkflowMode
    project_id: str | None = None
    project_path: str | None = None
    handle_id: str | None = None
    run_id: str | None = None
    steps: list[DsimWorkflowStep] = Field(default_factory=list)
    artifacts: list[DsimArtifactRef] = Field(default_factory=list)
    memory_candidates: list[DsimMemoryCandidate] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class DsimParameterDiff(BaseModel):
    name: str
    before: Any = None
    after: Any = None


class DsimRunComparison(BaseModel):
    first_run_id: str | None = None
    second_run_id: str | None = None
    status_changed: bool = False
    parameter_diffs: list[DsimParameterDiff] = Field(default_factory=list)
    metric_diffs: dict[str, Any] = Field(default_factory=dict)


class DsimSweepSummary(BaseModel):
    project_id: str
    handle_id: str | None = None
    combination_count: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)
