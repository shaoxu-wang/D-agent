"""Reusable MCP step helpers for DSim workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.workflow_utils import (
    extract_run_id,
    parameters_from_combination,
    step_from_tool_result,
    structured_payload,
)

if TYPE_CHECKING:
    from cc.dsim.runtime import DsimRuntimeBundle
    from cc.dsim.workflow_models import DsimWorkflowStep


async def open_project_from_path(
    *,
    runtime: DsimRuntimeBundle,
    project_id: str | None,
    project_path: str,
    steps: list[DsimWorkflowStep],
) -> tuple[Any, str | None, str | None]:
    """Open a DSim project through MCP and persist the active context."""
    open_input: dict[str, Any] = {"path": project_path}
    if project_id:
        open_input["project_id"] = project_id
    open_result = await runtime.invoker.call("mcp__dsim__OpenDsimProject", open_input)
    steps.append(step_from_tool_result("open_project", "mcp__dsim__OpenDsimProject", open_result))
    if open_result.is_error:
        return open_result, project_id, None

    open_payload = structured_payload(open_result)
    open_data = open_payload.get("data") or {}
    open_runtime = open_payload.get("runtime") or {}
    resolved_project_id = str(open_runtime.get("project_id") or open_data.get("project_id") or project_id or "") or None
    handle_id = str(open_data.get("handle_id") or open_runtime.get("handle_id") or "") or None
    if resolved_project_id:
        runtime.state_manager.upsert_project(project_id=resolved_project_id, project_path=project_path)
        runtime.state_manager.set_active_context(project_id=resolved_project_id, handle_id=handle_id, run_id=None)
    return open_result, resolved_project_id, handle_id


async def configure_run(
    *,
    runtime: DsimRuntimeBundle,
    handle_id: str,
    config: dict[str, Any],
    steps: list[DsimWorkflowStep],
) -> Any:
    result = await runtime.invoker.call(
        "mcp__dsim__ConfigureDsimRun",
        {"handle_id": handle_id, "config": config},
    )
    steps.append(step_from_tool_result("configure_run", "mcp__dsim__ConfigureDsimRun", result))
    return result


async def update_parameters(
    *,
    runtime: DsimRuntimeBundle,
    handle_id: str,
    parameters: list[dict[str, Any]],
    steps: list[DsimWorkflowStep],
    step_name: str = "update_parameters",
) -> Any:
    result = await runtime.invoker.call(
        "mcp__dsim__UpdateDsimParameters",
        {"handle_id": handle_id, "parameters": parameters},
    )
    steps.append(step_from_tool_result(step_name, "mcp__dsim__UpdateDsimParameters", result))
    return result


async def run_simulation(
    *,
    runtime: DsimRuntimeBundle,
    handle_id: str,
    timeout_seconds: int,
    steps: list[DsimWorkflowStep],
    step_name: str = "run_simulation",
) -> Any:
    result = await runtime.invoker.call(
        "mcp__dsim__RunDsimSimulation",
        {"handle_id": handle_id, "timeout_seconds": timeout_seconds},
    )
    steps.append(step_from_tool_result(step_name, "mcp__dsim__RunDsimSimulation", result))
    return result


async def read_curve_summary(
    *,
    runtime: DsimRuntimeBundle,
    project_id: str | None,
    handle_id: str,
    run_id: str | None,
    steps: list[DsimWorkflowStep],
    summary: dict[str, Any],
) -> None:
    result = await runtime.invoker.call(
        "mcp__dsim__ReadDsimCurves",
        {"handle_id": handle_id, "mode": "summary"},
    )
    steps.append(step_from_tool_result("read_curve_summary", "mcp__dsim__ReadDsimCurves", result))
    payload = structured_payload(result)
    if result.is_error:
        summary["curve_error"] = payload.get("error")
        return

    curve_summary = dict(payload.get("data") or {})
    if run_id is not None and "run_id" not in curve_summary:
        curve_summary["run_id"] = str(run_id)
    summary["curve_summary"] = curve_summary
    if project_id:
        runtime.state_manager.append_curve_summary(project_id=project_id, summary=curve_summary)


async def run_sweep_combinations(
    *,
    runtime: DsimRuntimeBundle,
    handle_id: str | None,
    combinations: list[dict[str, Any]],
    timeout_seconds: int,
    steps: list[DsimWorkflowStep],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not handle_id:
        return results

    for index, combination in enumerate(combinations, start=1):
        parameters = parameters_from_combination(combination)
        if parameters:
            update_result = await update_parameters(
                runtime=runtime,
                handle_id=handle_id,
                parameters=parameters,
                steps=steps,
                step_name=f"sweep_update_{index}",
            )
            if update_result.is_error:
                results.append({"index": index, "ok": False, "error": structured_payload(update_result).get("error")})
                continue

        run_result = await run_simulation(
            runtime=runtime,
            handle_id=handle_id,
            timeout_seconds=timeout_seconds,
            steps=steps,
            step_name=f"sweep_run_{index}",
        )
        payload = structured_payload(run_result)
        results.append(
            {
                "index": index,
                "ok": not run_result.is_error,
                "combination": combination,
                "run_id": extract_run_id(payload),
                "error": payload.get("error"),
            }
        )
    return results
