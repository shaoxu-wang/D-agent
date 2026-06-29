"""Deterministic DSim failure diagnosis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DiagnosisSummary:
    category: str
    severity: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "next_actions": self.next_actions,
        }


class DsimDiagnosisProcessor:
    """Classify DSim run failures from stored run and curve summaries."""

    def diagnose(
        self,
        *,
        run_id: str | None,
        status: str | None,
        error: dict[str, Any],
        curve_summary: dict[str, Any] | None,
    ) -> DiagnosisSummary:
        normalized_status = str(status or "").lower()
        error_code = str(error.get("code") or "").upper()
        message = str(error.get("message") or "")
        evidence = [item for item in [f"run_id={run_id}" if run_id else "", error_code, message] if item]

        if _is_parameter_update_failure(error_code, message):
            return DiagnosisSummary(
                category="parameter_update_failed",
                severity="high",
                confidence=0.85,
                evidence=evidence,
                next_actions=[
                    "Validate parameter names, ranges, and units before starting another run.",
                    "Retry with one parameter change at a time to isolate the invalid update.",
                ],
            )

        if _is_timeout(normalized_status, error_code, message):
            evidence.append("Simulation timeout detected from status, error code, or message.")
            return DiagnosisSummary(
                category="simulation_timeout",
                severity="high",
                confidence=0.8,
                evidence=evidence,
                next_actions=[
                    "Increase timeout only after checking model size and solver settings.",
                    "Run a narrower configuration to confirm whether the timeout is reproducible.",
                ],
            )

        if error_code == "SOLVER_FAILED":
            if curve_summary:
                evidence.append(f"curve_summary={curve_summary}")
            return DiagnosisSummary(
                category="solver_convergence",
                severity="high",
                confidence=0.85,
                evidence=evidence,
                next_actions=[
                    "Review solver tolerance and maximum iterations.",
                    "Compare curve shape with the last successful run.",
                ],
            )

        if curve_summary and curve_summary.get("empty") is True:
            evidence.append("Curve summary is empty or missing usable curve data.")
            return DiagnosisSummary(
                category="empty_curve_result",
                severity="medium",
                confidence=0.75,
                evidence=evidence,
                next_actions=[
                    "Verify curve export settings.",
                    "Re-run curve extraction before interpreting simulation quality.",
                ],
            )

        if _has_curve_anomaly(curve_summary):
            evidence.append(f"Curve summary anomaly marker or threshold was detected: {curve_summary}")
            return DiagnosisSummary(
                category="curve_summary_anomaly",
                severity="medium",
                confidence=0.7,
                evidence=evidence,
                next_actions=[
                    "Compare the anomalous curve summary with the last known stable run.",
                    "Review the parameters that changed immediately before this run.",
                ],
            )

        if normalized_status == "failed" and not error_code and not curve_summary:
            evidence.append("Missing diagnostic evidence: no error code and no curve summary were available.")
            return DiagnosisSummary(
                category="missing_diagnostic_evidence",
                severity="medium",
                confidence=0.65,
                evidence=evidence,
                next_actions=[
                    "Re-run with structured error capture enabled.",
                    "Read curve summary before making engineering conclusions.",
                ],
            )

        if _is_simulation_failure(error_code):
            return DiagnosisSummary(
                category="simulation_failed",
                severity="high",
                confidence=0.7,
                evidence=evidence,
                next_actions=[
                    "Inspect raw DSim error output and rerun with a narrower configuration.",
                    "Compare against the latest successful run to identify changed inputs.",
                ],
            )

        if normalized_status == "failed":
            return DiagnosisSummary(
                category="unknown_failure",
                severity="medium",
                confidence=0.45,
                evidence=evidence,
                next_actions=["Inspect raw DSim error output and rerun with a narrower configuration."],
            )

        return DiagnosisSummary(
            category="no_failure_detected",
            severity="low",
            confidence=0.6,
            evidence=evidence,
            next_actions=["No failure-specific action is required from stored summaries."],
        )


def _is_parameter_update_failure(error_code: str, message: str) -> bool:
    message_lower = message.lower()
    message_says_parameter_failure = "parameter" in message_lower and any(
        token in message_lower for token in ("invalid", "failed", "out of range")
    )
    return (
        error_code in {"PARAMETER_UPDATE_FAILED", "PARAMETER_VALIDATION_FAILED", "INVALID_PARAMETER"}
        or message_says_parameter_failure
    )


def _is_timeout(status: str, error_code: str, message: str) -> bool:
    return (
        status == "timeout"
        or error_code in {"TIMEOUT", "RUN_TIMEOUT", "SIMULATION_TIMEOUT"}
        or "timeout" in message.lower()
    )


def _is_simulation_failure(error_code: str) -> bool:
    return error_code in {"SIMULATION_FAILED", "RUN_FAILED", "EXECUTION_FAILED"}


def _has_curve_anomaly(curve_summary: dict[str, Any] | None) -> bool:
    if not curve_summary:
        return False
    if curve_summary.get("anomaly") is True or curve_summary.get("anomalous") is True:
        return True
    metrics = curve_summary.get("metrics")
    if not isinstance(metrics, dict):
        return False
    return any(isinstance(value, int | float) and abs(value) >= 1_000_000 for value in metrics.values())
