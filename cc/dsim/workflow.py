"""Stage 2A DSim workflow orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.workflow_models import (
    DsimArtifactRef,
    DsimMemoryCandidate,
    DsimWorkflowMode,
    DsimWorkflowRequest,
    DsimWorkflowResult,
    DsimWorkflowStep,
)
from cc.dsim.workflow_steps import (
    configure_run,
    open_project_from_path,
    read_curve_summary,
    run_simulation,
    run_sweep_combinations,
    update_parameters,
)
from cc.dsim.workflow_utils import (
    extract_run_id,
    render_report_markdown,
    resolve_run_for_compare,
    stored_curve_summary,
    stored_run_summary,
    structured_payload,
    workflow_error_result,
    workflow_result_from_tool_failure,
)

if TYPE_CHECKING:
    from cc.dsim.runtime import DsimRuntimeBundle


class DsimWorkflowService:
    """Orchestrate Stage 2A DSim workflows through the runtime bundle."""

    def __init__(self, *, runtime: DsimRuntimeBundle) -> None:
        self._runtime = runtime

    async def run(self, request: DsimWorkflowRequest) -> DsimWorkflowResult:
        if request.mode == DsimWorkflowMode.inspect_only:
            return self.inspect_project(request)
        if request.mode == DsimWorkflowMode.single_run:
            return await self.run_single(request.model_dump())
        if request.mode == DsimWorkflowMode.diagnose_existing:
            return await self.diagnose_existing(request.model_dump())
        if request.mode == DsimWorkflowMode.report_existing:
            return await self.generate_report(request.model_dump())
        if request.mode == DsimWorkflowMode.sweep:
            return await self.run_sweep(request.model_dump())
        raise ValueError(f"Unsupported DSim workflow mode: {request.mode}")

    def inspect_project(self, request: DsimWorkflowRequest) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(request.model_dump())
        summary = {
            "ok": True,
            "mode": request.mode.value,
            "project_id": project_id,
            "active_context": self._active_context_summary(),
        }
        if project_id:
            self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)
        return DsimWorkflowResult(
            mode=request.mode,
            project_id=project_id,
            project_path=request.project_path,
            handle_id=request.handle_id,
            run_id=request.run_id,
            steps=[DsimWorkflowStep(name="inspect_project", status="completed", state_written=bool(project_id))],
            summary=summary,
        )

    async def save_project_context(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        if not project_id:
            return workflow_error_result(
                mode=DsimWorkflowMode.inspect_only,
                summary={"saved": False, "error": "project_id is required"},
                step_name="save_project_context",
            )

        if project_path := tool_input.get("project_path"):
            self._runtime.state_manager.upsert_project(project_id=project_id, project_path=str(project_path))

        summary = {
            "saved": True,
            "mode": DsimWorkflowMode.inspect_only.value,
            "kind": tool_input.get("kind", "note"),
            "content": tool_input.get("content", ""),
            "confirmed": bool(tool_input.get("confirmed")),
        }
        self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)

        memory_candidates: list[DsimMemoryCandidate] = []
        if summary["kind"] in {"conclusion", "preference", "recommendation"} and summary["confirmed"]:
            candidate = DsimMemoryCandidate(
                kind=str(summary["kind"]),
                evidence_refs=[{"source": "SaveProjectContext", "project_id": project_id}],
                confirmed=True,
            )
            memory_candidates.append(candidate)
            self._runtime.state_manager.record_memory_candidate(
                project_id=project_id,
                candidate=candidate.model_dump(),
            )

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.inspect_only,
            project_id=project_id,
            steps=[DsimWorkflowStep(name="save_project_context", status="completed", state_written=True)],
            memory_candidates=memory_candidates,
            summary=summary,
        )

    async def run_single(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        handle_id = self._resolve_handle_id(tool_input)
        project_path = tool_input.get("project_path")
        steps: list[DsimWorkflowStep] = []
        if not handle_id and project_path:
            open_result, project_id, handle_id = await open_project_from_path(
                runtime=self._runtime,
                project_id=project_id,
                project_path=str(project_path),
                steps=steps,
            )
            if open_result.is_error:
                return workflow_result_from_tool_failure(
                    mode=DsimWorkflowMode.single_run,
                    project_id=project_id,
                    handle_id=handle_id,
                    steps=steps,
                    result=open_result,
                )

        if not handle_id:
            return workflow_error_result(
                mode=DsimWorkflowMode.single_run,
                project_id=project_id,
                summary={"ok": False, "error": "handle_id is required"},
                step_name="run_single",
            )

        if config := tool_input.get("config"):
            config_result = await configure_run(
                runtime=self._runtime,
                handle_id=handle_id,
                config=config,
                steps=steps,
            )
            if config_result.is_error:
                return workflow_result_from_tool_failure(
                    mode=DsimWorkflowMode.single_run,
                    project_id=project_id,
                    handle_id=handle_id,
                    steps=steps,
                    result=config_result,
                )

        parameters = list(tool_input.get("parameters", []))
        if parameters:
            update_result = await update_parameters(
                runtime=self._runtime,
                handle_id=handle_id,
                parameters=parameters,
                steps=steps,
            )
            if update_result.is_error:
                return workflow_result_from_tool_failure(
                    mode=DsimWorkflowMode.single_run,
                    project_id=project_id,
                    handle_id=handle_id,
                    steps=steps,
                    result=update_result,
                )

        timeout_seconds = int(tool_input.get("timeout_seconds") or 1800)
        run_result = await run_simulation(
            runtime=self._runtime,
            handle_id=handle_id,
            timeout_seconds=timeout_seconds,
            steps=steps,
        )

        payload = structured_payload(run_result)
        run_id = extract_run_id(payload) or tool_input.get("run_id")
        summary = {
            "ok": not run_result.is_error,
            "mode": DsimWorkflowMode.single_run.value,
            "run_id": run_id,
            "status": payload.get("data", {}).get("status"),
            "error": payload.get("error"),
        }
        if not run_result.is_error:
            await read_curve_summary(
                runtime=self._runtime,
                project_id=project_id,
                handle_id=handle_id,
                run_id=run_id,
                steps=steps,
                summary=summary,
            )

        if project_id:
            self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)
            self._runtime.state_manager.append_run_summary(project_id=project_id, summary=summary)
            self._runtime.state_manager.set_active_context(
                project_id=project_id,
                handle_id=handle_id,
                run_id=str(run_id) if run_id is not None else None,
            )

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.single_run,
            project_id=project_id,
            handle_id=handle_id,
            run_id=str(run_id) if run_id is not None else None,
            steps=steps,
            summary=summary,
        )

    async def diagnose_existing(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        run_id = str(tool_input.get("run_id", "")) or None
        stored_run = stored_run_summary(self._runtime.state_manager, project_id, run_id)
        error = tool_input.get("error") or {}
        if stored_run and not error:
            error = stored_run.get("error") or {}
        curve_summary = stored_curve_summary(self._runtime.state_manager, project_id, run_id)

        summary = {
            "ok": True,
            "mode": DsimWorkflowMode.diagnose_existing.value,
            "run_id": run_id,
            "status": tool_input.get("status") or (stored_run or {}).get("status"),
            "error_code": error.get("code", "UNKNOWN_FAILURE") if isinstance(error, dict) else "UNKNOWN_FAILURE",
            "message": error.get("message", "") if isinstance(error, dict) else str(error),
        }
        if curve_summary:
            summary["curve_summary"] = curve_summary
        if project_id:
            self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.diagnose_existing,
            project_id=project_id,
            run_id=run_id,
            steps=[DsimWorkflowStep(name="diagnose_existing", status="completed", state_written=bool(project_id))],
            summary=summary,
        )

    async def generate_report(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        if not project_id:
            return workflow_error_result(
                mode=DsimWorkflowMode.report_existing,
                summary={"ok": False, "error": "project_id is required"},
                step_name="generate_report",
            )

        runs = list(tool_input.get("runs", [])) or self._runtime.state_manager.list_run_summaries(project_id)
        markdown = render_report_markdown(project_id=project_id, runs=runs)
        artifact_ref = DsimArtifactRef(
            **self._runtime.artifact_store.write_report(project_id=project_id, markdown=markdown)
        )
        self._runtime.state_manager.add_artifact_ref(project_id=project_id, artifact_ref=artifact_ref.model_dump())

        summary = {
            "ok": True,
            "mode": DsimWorkflowMode.report_existing.value,
            "run_count": len(runs),
            "artifact_id": artifact_ref.artifact_id,
        }
        self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.report_existing,
            project_id=project_id,
            steps=[
                DsimWorkflowStep(
                    name="generate_report",
                    status="completed",
                    state_written=True,
                    artifact_written=True,
                )
            ],
            artifacts=[artifact_ref],
            summary=summary,
        )

    async def compare_runs(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        runs = list(tool_input.get("runs", []))
        if len(runs) < 2:
            return workflow_error_result(
                mode=DsimWorkflowMode.report_existing,
                project_id=project_id,
                summary={"ok": False, "error": "at least two runs are required"},
                step_name="compare_runs",
            )

        first = resolve_run_for_compare(self._runtime.state_manager, project_id, runs[0])
        second = resolve_run_for_compare(self._runtime.state_manager, project_id, runs[1])
        summary = {
            "ok": True,
            "mode": "compare_runs",
            "first_run_id": first.get("run_id"),
            "second_run_id": second.get("run_id"),
            "first_status": first.get("status"),
            "second_status": second.get("status"),
            "status_changed": first.get("status") != second.get("status"),
        }
        if project_id:
            self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.report_existing,
            project_id=project_id,
            steps=[DsimWorkflowStep(name="compare_runs", status="completed", state_written=bool(project_id))],
            summary=summary,
        )

    async def run_sweep(self, tool_input: dict[str, Any]) -> DsimWorkflowResult:
        project_id = self._resolve_project_id(tool_input)
        if not project_id:
            return workflow_error_result(
                mode=DsimWorkflowMode.sweep,
                summary={"ok": False, "error": "project_id is required"},
                step_name="run_sweep",
            )

        combinations = list(tool_input.get("combinations", []))
        handle_id = self._resolve_handle_id(tool_input)
        steps: list[DsimWorkflowStep] = []
        timeout_seconds = int(tool_input.get("timeout_seconds") or 1800)
        results = await run_sweep_combinations(
            runtime=self._runtime,
            handle_id=handle_id,
            combinations=combinations,
            timeout_seconds=timeout_seconds,
            steps=steps,
        )

        summary = {
            "ok": True,
            "mode": DsimWorkflowMode.sweep.value,
            "project_id": project_id,
            "handle_id": handle_id,
            "combination_count": len(combinations),
            "results": results,
        }
        artifact_ref = DsimArtifactRef(
            **self._runtime.artifact_store.write_sweep_summary(project_id=project_id, summary=summary)
        )
        self._runtime.state_manager.append_sweep_summary(project_id=project_id, summary=summary)
        self._runtime.state_manager.add_artifact_ref(project_id=project_id, artifact_ref=artifact_ref.model_dump())

        return DsimWorkflowResult(
            mode=DsimWorkflowMode.sweep,
            project_id=project_id,
            handle_id=handle_id,
            steps=steps
            or [
                DsimWorkflowStep(
                    name="run_sweep",
                    status="completed",
                    state_written=True,
                    artifact_written=True,
                )
            ],
            artifacts=[artifact_ref],
            summary=summary,
        )

    def _resolve_project_id(self, tool_input: dict[str, Any]) -> str | None:
        if project_id := tool_input.get("project_id"):
            return str(project_id)
        context = self._runtime.state_manager.get_active_context()
        if context and context.active_project_id:
            return context.active_project_id
        return None

    def _resolve_handle_id(self, tool_input: dict[str, Any]) -> str | None:
        if handle_id := tool_input.get("handle_id"):
            return str(handle_id)
        context = self._runtime.state_manager.get_active_context()
        if context and context.active_handle_id:
            return context.active_handle_id
        return None

    def _active_context_summary(self) -> dict[str, Any]:
        context = self._runtime.state_manager.get_active_context()
        if context is None:
            return {}
        return context.model_dump()
