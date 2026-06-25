import pytest
from pydantic import ValidationError

from cc.dsim.workflow_models import (
    DsimArtifactRef,
    DsimMemoryCandidate,
    DsimParameterDiff,
    DsimRunComparison,
    DsimSweepSummary,
    DsimWorkflowMode,
    DsimWorkflowRequest,
    DsimWorkflowResult,
)


def test_workflow_request_requires_explicit_mode() -> None:
    with pytest.raises(ValidationError):
        DsimWorkflowRequest()


def test_workflow_mode_accepts_supported_values() -> None:
    assert DsimWorkflowMode("inspect_only") == "inspect_only"
    assert DsimWorkflowMode("single_run") == "single_run"


def test_workflow_result_serializes_without_raw_tool_result() -> None:
    result = DsimWorkflowResult(
        mode=DsimWorkflowMode.single_run,
        project_id="project-1",
        handle_id="handle-1",
        summary={"status": "completed"},
    )

    dumped = result.model_dump()

    assert dumped["handle_id"] == "handle-1"
    assert "tool_result" not in dumped


def test_artifact_ref_requires_storage_key_and_keeps_local_path() -> None:
    ref = DsimArtifactRef(
        artifact_id="report-1",
        kind="report",
        path="C:/workspace/.dsim_agent/reports/report-1.md",
        storage_key="local/reports/report-1.md",
        uri=None,
        mime_type="text/markdown",
    )

    assert ref.storage_key == "local/reports/report-1.md"
    assert ref.path.endswith("report-1.md")
    assert ref.uri is None


def test_memory_candidate_tracks_evidence_and_confirmation() -> None:
    candidate = DsimMemoryCandidate(
        kind="preference",
        evidence_refs=[{"source": "SaveProjectContext", "project_id": "project-1"}],
        confirmed=True,
    )

    assert candidate.confirmed is True
    assert candidate.evidence_refs[0]["project_id"] == "project-1"


def test_derived_workflow_models_capture_comparison_and_sweep_shape() -> None:
    diff = DsimParameterDiff(name="alpha", before=1, after=2)
    comparison = DsimRunComparison(
        first_run_id="run-1",
        second_run_id="run-2",
        status_changed=True,
        parameter_diffs=[diff],
        metric_diffs={"peak": 0.5},
    )
    sweep = DsimSweepSummary(
        project_id="project-1",
        handle_id="handle-1",
        combination_count=2,
        results=[{"index": 1, "ok": True}],
    )

    assert comparison.parameter_diffs[0].name == "alpha"
    assert comparison.metric_diffs["peak"] == 0.5
    assert sweep.combination_count == 2
