"""Helpers for DSim workflow orchestration."""

from __future__ import annotations

from typing import Any, cast

from cc.dsim.workflow_models import DsimWorkflowMode, DsimWorkflowResult, DsimWorkflowStep


def structured_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "metadata", {}).get("structured")
    return payload if isinstance(payload, dict) else {}


def extract_run_id(payload: dict[str, Any]) -> str | None:
    runtime = payload.get("runtime") or {}
    data = payload.get("data") or {}
    run_id = runtime.get("run_id") or data.get("run_id")
    return str(run_id) if run_id is not None else None


def step_from_tool_result(name: str, tool_name: str, result: Any) -> DsimWorkflowStep:
    payload = structured_payload(result)
    error = payload.get("error") or {}
    return DsimWorkflowStep(
        name=name,
        status="failed" if result.is_error else "completed",
        tool_name=tool_name,
        error_code=error.get("code") if isinstance(error, dict) else None,
        error_message=error.get("message") if isinstance(error, dict) else None,
        state_written=bool(payload.get("state_updates")),
        artifact_written=bool(payload.get("artifacts")),
    )


def render_report_markdown(*, project_id: str, runs: list[dict[str, Any]]) -> str:
    lines = [f"# DSim Report: {project_id}", ""]
    if not runs:
        lines.append("No run summaries are available.")
    else:
        lines.extend(["## Runs", ""])
        for run in runs:
            run_id = run.get("run_id", "unknown-run")
            status = run.get("status", "unknown")
            lines.append(f"- {run_id}: {status}")
    lines.append("")
    return "\n".join(lines)


def parameters_from_combination(combination: Any) -> list[dict[str, Any]]:
    if isinstance(combination, dict) and isinstance(combination.get("parameters"), list):
        return list(combination["parameters"])
    if isinstance(combination, dict) and "parameter" in combination:
        return [{"name": combination.get("parameter"), "value": combination.get("value")}]
    if isinstance(combination, dict) and "name" in combination:
        return [{"name": combination.get("name"), "value": combination.get("value")}]
    return []


def stored_run_summary(state_manager: Any, project_id: str | None, run_id: str | None) -> dict[str, Any] | None:
    if not project_id or not run_id:
        return None
    return cast("dict[str, Any] | None", state_manager.get_run_summary(project_id, run_id))


def stored_curve_summary(state_manager: Any, project_id: str | None, run_id: str | None) -> dict[str, Any] | None:
    if not project_id or not run_id or not hasattr(state_manager, "get_curve_summary"):
        return None
    return cast("dict[str, Any] | None", state_manager.get_curve_summary(project_id, run_id))


def resolve_run_for_compare(state_manager: Any, project_id: str | None, run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run.get("run_id", "")) or None
    stored_run = stored_run_summary(state_manager, project_id, run_id)
    if stored_run is None:
        return run
    merged = dict(stored_run)
    merged.update({key: value for key, value in run.items() if value is not None})
    return merged


def workflow_error_result(
    *,
    mode: DsimWorkflowMode,
    summary: dict[str, Any],
    step_name: str,
    project_id: str | None = None,
) -> DsimWorkflowResult:
    return DsimWorkflowResult(
        mode=mode,
        project_id=project_id,
        steps=[DsimWorkflowStep(name=step_name, status="failed", error_message=str(summary.get("error", "")))],
        summary=summary,
    )


def workflow_result_from_tool_failure(
    *,
    mode: DsimWorkflowMode,
    project_id: str | None,
    handle_id: str | None,
    steps: list[DsimWorkflowStep],
    result: Any,
) -> DsimWorkflowResult:
    payload = structured_payload(result)
    return DsimWorkflowResult(
        mode=mode,
        project_id=project_id,
        handle_id=handle_id,
        steps=steps,
        summary={"ok": False, "error": payload.get("error"), "content": result.text},
    )
