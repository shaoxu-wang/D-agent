from cc.dsim.diagnosis import DsimDiagnosisProcessor


def test_diagnosis_processor_classifies_solver_failure_with_curve_evidence() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-1",
        status="failed",
        error={"code": "SOLVER_FAILED", "message": "Solver did not converge."},
        curve_summary={"run_id": "run-1", "metrics": {"peak": 5.0}, "empty": False},
    )

    assert summary.category == "solver_convergence"
    assert summary.severity == "high"
    assert summary.confidence >= 0.8
    assert any("SOLVER_FAILED" in item for item in summary.evidence)
    assert any("tolerance" in action.lower() for action in summary.next_actions)


def test_diagnosis_processor_flags_missing_curve_data() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-2",
        status="completed",
        error={},
        curve_summary={"run_id": "run-2", "empty": True},
    )

    assert summary.category == "empty_curve_result"
    assert summary.severity == "medium"
    assert any("curve" in item.lower() for item in summary.evidence)


def test_diagnosis_processor_classifies_parameter_update_failure() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id=None,
        status="failed",
        error={"code": "PARAMETER_UPDATE_FAILED", "message": "Invalid parameter alpha."},
        curve_summary=None,
    )

    assert summary.category == "parameter_update_failed"
    assert summary.severity == "high"
    assert any("parameter" in action.lower() for action in summary.next_actions)


def test_diagnosis_processor_classifies_simulation_timeout() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-timeout",
        status="timeout",
        error={"code": "TIMEOUT", "message": "Simulation timed out."},
        curve_summary=None,
    )

    assert summary.category == "simulation_timeout"
    assert summary.severity == "high"
    assert any("timeout" in item.lower() for item in summary.evidence)


def test_diagnosis_processor_classifies_curve_anomaly_from_summary_marker() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-anomaly",
        status="completed",
        error={},
        curve_summary={"run_id": "run-anomaly", "anomaly": True, "metrics": {"peak": 9999.0}},
    )

    assert summary.category == "curve_summary_anomaly"
    assert summary.severity == "medium"
    assert any("anomaly" in item.lower() for item in summary.evidence)


def test_diagnosis_processor_classifies_missing_diagnostic_evidence() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-missing",
        status="failed",
        error={},
        curve_summary=None,
    )

    assert summary.category == "missing_diagnostic_evidence"
    assert summary.severity == "medium"
    assert any("missing" in item.lower() for item in summary.evidence)


def test_diagnosis_processor_classifies_generic_simulation_failure() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-failed",
        status="failed",
        error={"code": "SIMULATION_FAILED", "message": "Native run failed."},
        curve_summary={"run_id": "run-failed", "empty": False},
    )

    assert summary.category == "simulation_failed"
    assert summary.severity == "high"
    assert any("rerun" in action.lower() for action in summary.next_actions)


def test_diagnosis_processor_keeps_unknown_failure_for_unrecognized_failure_signal() -> None:
    summary = DsimDiagnosisProcessor().diagnose(
        run_id="run-unknown",
        status="failed",
        error={"code": "NATIVE_ERROR", "message": "Native backend returned an unknown failure."},
        curve_summary={"run_id": "run-unknown", "empty": False},
    )

    assert summary.category == "unknown_failure"
    assert summary.severity == "medium"
    assert summary.confidence < 0.5
