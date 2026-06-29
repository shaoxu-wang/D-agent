"""Stage 2A DSim workflow orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.diagnosis import DsimDiagnosisProcessor
from cc.dsim.memory_context import MemoryContextBuilder
from cc.dsim.memory_kinds import STAGE2C_MEMORY_KINDS
from cc.dsim.run_plan import RunPlanApplyMode, RunPlanBuilder
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

        kind = str(tool_input.get("kind", "project_fact"))
        confirmed = bool(tool_input.get("confirmed"))
        if kind not in STAGE2C_MEMORY_KINDS:
            return workflow_error_result(
                mode=DsimWorkflowMode.inspect_only,
                project_id=project_id,
                summary={
                    "saved": False,
                    "error": f"Unsupported DSim memory kind: {kind}",
                    "supported_kinds": sorted(STAGE2C_MEMORY_KINDS),
                },
                step_name="save_project_context",
            )

        summary = {
            "saved": True,
            "mode": DsimWorkflowMode.inspect_only.value,
            "kind": kind,
            "content": tool_input.get("content", ""),
            "confirmed": confirmed,
        }
        self._runtime.state_manager.append_workflow_summary(project_id=project_id, summary=summary)

        memory_candidates: list[DsimMemoryCandidate] = []
        if confirmed:
            candidate = DsimMemoryCandidate(
                kind=kind,
                content=str(tool_input.get("content", "")),
                applies_to=list(tool_input.get("applies_to", [])),
                evidence_refs=[{"source": "SaveProjectContext", "project_id": project_id}],
                confirmed=True,
                priority=int(tool_input.get("priority") or 0),
            )
            memory_candidates.append(candidate)
            candidate_payload = candidate.model_dump()
            memory_sink = getattr(self._runtime, "memory_sink", None)
            if memory_sink is not None and hasattr(memory_sink, "save_confirmed"):
                memory_sink.save_confirmed(candidate=candidate_payload, context={"project_id": project_id})
            else:
                self._runtime.state_manager.record_memory_candidate(
                    project_id=project_id,
                    candidate=candidate_payload,
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

        run_plan = None
        if project_id and tool_input.get("use_project_memory"):
            memory_context = MemoryContextBuilder(reader=self._runtime.state_manager).build(
                project_id=project_id,
                applies_to=DsimWorkflowMode.single_run.value,
            )
            run_plan = RunPlanBuilder().build(
                mode=DsimWorkflowMode.single_run.value,
                memory_context=memory_context,
                apply_mode=self._memory_usage_mode(tool_input),
            )
            if run_plan.apply_mode == "apply_prefill":
                merged_config = {**run_plan.config_prefill, **dict(tool_input.get("config") or {})}
                merged_parameters = [*run_plan.parameter_prefill, *list(tool_input.get("parameters", []))]
                tool_input = {**tool_input, "config": merged_config, "parameters": merged_parameters}

        config_input = tool_input.get("config")
        if isinstance(config_input, dict) and config_input:
            config_result = await configure_run(
                runtime=self._runtime,
                handle_id=handle_id,
                config=config_input,
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
        if run_plan is not None:
            summary["run_plan"] = run_plan.compact()
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
        status_value = summary.get("status")
        diagnosis = DsimDiagnosisProcessor().diagnose(
            run_id=run_id,
            status=str(status_value) if status_value is not None else None,
            error=error if isinstance(error, dict) else {"message": str(error)},
            curve_summary=curve_summary,
        )
        summary["diagnosis"] = diagnosis.model_dump()
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
        runs = self._merge_report_workflow_context(project_id=project_id, runs=runs)
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
            project_id=project_id,
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

    def _merge_report_workflow_context(self, *, project_id: str, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not hasattr(self._runtime.state_manager, "list_workflow_summaries"):
            return runs
        by_run_id: dict[str, dict[str, Any]] = {}
        for summary in self._runtime.state_manager.list_workflow_summaries(project_id):
            run_id = summary.get("run_id")
            if run_id is None:
                continue
            context = by_run_id.setdefault(str(run_id), {})
            for key in ("diagnosis", "run_plan"):
                if key in summary:
                    context[key] = summary[key]

        merged: list[dict[str, Any]] = []
        for run in runs:
            run_id = run.get("run_id")
            if run_id is None:
                merged.append(run)
                continue
            merged.append({**by_run_id.get(str(run_id), {}), **run})
        return merged

    def _memory_usage_mode(self, tool_input: dict[str, Any]) -> RunPlanApplyMode:
        mode = str(tool_input.get("memory_usage_mode") or "suggest_only")
        return "apply_prefill" if mode == "apply_prefill" else "suggest_only"
