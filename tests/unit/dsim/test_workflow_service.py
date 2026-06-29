import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from cc.dsim.artifacts import DsimArtifactStore
from cc.dsim.runtime import DsimRuntimeBundle
from cc.dsim.state import DsimProjectStateManager
from cc.dsim.workflow import DsimWorkflowService
from cc.dsim.workflow_models import DsimWorkflowMode, DsimWorkflowRequest
from cc.tools.base import ToolResult


def test_workflow_service_requires_mode() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service = DsimWorkflowService(
        runtime=DsimRuntimeBundle(
            registry=object(),
            permission_ctx=object(),
            state_manager=object(),
            audit_logger=object(),
            observer=object(),
            invoker=object(),
            artifact_store=DsimArtifactStore(workspace=workspace),
            workflow_service=object(),
            memory_sink=None,
        )
    )

    with pytest.raises(ValidationError):
        service.run(DsimWorkflowRequest())

    shutil.rmtree(workspace)


def _build_service(workspace: Path) -> tuple[DsimWorkflowService, DsimProjectStateManager]:
    state_manager = DsimProjectStateManager(workspace=workspace, session_id="session-1")
    service = DsimWorkflowService(
        runtime=DsimRuntimeBundle(
            registry=object(),
            permission_ctx=object(),
            state_manager=state_manager,
            audit_logger=object(),
            observer=object(),
            invoker=object(),
            artifact_store=DsimArtifactStore(workspace=workspace),
            workflow_service=object(),
            memory_sink=None,
        )
    )
    return service, state_manager


class RecordingInvoker:
    def __init__(self, results: list[ToolResult] | None = None) -> None:
        self.calls = []
        self.results = list(results or [])

    async def call(self, tool_name: str, tool_input: dict) -> ToolResult:
        self.calls.append((tool_name, tool_input))
        if self.results:
            return self.results.pop(0)
        return ToolResult(
            content="ok",
            metadata={
                "structured": {
                    "ok": True,
                    "service": "dsim",
                    "tool": tool_name.replace("mcp__dsim__", ""),
                    "data": {"status": "completed", "run_id": "run-1"},
                    "runtime": {"run_id": "run-1"},
                    "state_updates": [],
                    "artifacts": [],
                    "error": None,
                }
            },
        )


class RecordingMemorySink:
    def __init__(self) -> None:
        self.calls = []

    def save_confirmed(self, *, candidate: dict, context: dict) -> dict:
        self.calls.append({"candidate": candidate, "context": context})
        return {**candidate, "long_term_memory_status": "deferred"}


def _structured_tool_result(
    *,
    tool_name: str,
    data: dict | None = None,
    runtime: dict | None = None,
    error: dict | None = None,
    is_error: bool = False,
) -> ToolResult:
    return ToolResult(
        content="ok" if not is_error else "error",
        is_error=is_error,
        metadata={
            "structured": {
                "ok": not is_error,
                "service": "dsim",
                "tool": tool_name,
                "data": data or {},
                "runtime": runtime or {},
                "state_updates": [],
                "artifacts": [],
                "error": error,
            }
        },
    )


def _build_service_with_invoker(
    workspace: Path,
    invoker: RecordingInvoker,
) -> tuple[DsimWorkflowService, DsimProjectStateManager]:
    state_manager = DsimProjectStateManager(workspace=workspace, session_id="session-1")
    service = DsimWorkflowService(
        runtime=DsimRuntimeBundle(
            registry=object(),
            permission_ctx=object(),
            state_manager=state_manager,
            audit_logger=object(),
            observer=object(),
            invoker=invoker,
            artifact_store=DsimArtifactStore(workspace=workspace),
            workflow_service=object(),
            memory_sink=None,
        )
    )
    return service, state_manager


def _build_service_with_memory_sink(
    workspace: Path,
    memory_sink: RecordingMemorySink,
) -> tuple[DsimWorkflowService, DsimProjectStateManager]:
    state_manager = DsimProjectStateManager(workspace=workspace, session_id="session-1")
    service = DsimWorkflowService(
        runtime=DsimRuntimeBundle(
            registry=object(),
            permission_ctx=object(),
            state_manager=state_manager,
            audit_logger=object(),
            observer=object(),
            invoker=object(),
            artifact_store=DsimArtifactStore(workspace=workspace),
            workflow_service=object(),
            memory_sink=memory_sink,
        )
    )
    return service, state_manager


@pytest.mark.asyncio
async def test_workflow_service_saves_confirmed_context_and_memory_candidate() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)

    result = await service.save_project_context(
        {
            "project_id": "project-1",
            "kind": "engineering_conclusion",
            "content": "Use the local mock backend.",
            "applies_to": ["single_run"],
            "priority": 2,
            "confirmed": True,
        }
    )

    project = state_manager.get_project("project-1")
    assert result.mode == DsimWorkflowMode.inspect_only
    assert result.summary["saved"] is True
    assert project is not None
    assert project.workflow_summaries
    assert project.memory_candidates
    assert project.memory_candidates[0]["kind"] == "engineering_conclusion"
    assert project.memory_candidates[0]["content"] == "Use the local mock backend."
    assert project.memory_candidates[0]["applies_to"] == ["single_run"]
    assert project.memory_candidates[0]["priority"] == 2
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_uses_memory_sink_for_confirmed_candidates() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    memory_sink = RecordingMemorySink()
    service, _state_manager = _build_service_with_memory_sink(workspace, memory_sink)

    result = await service.save_project_context(
        {
            "project_id": "project-memory",
            "kind": "user_preference",
            "content": "Keep reports local.",
            "applies_to": ["report_existing"],
            "confirmed": True,
        }
    )

    assert result.memory_candidates[0].kind == "user_preference"
    assert result.memory_candidates[0].content == "Keep reports local."
    assert result.memory_candidates[0].applies_to == ["report_existing"]
    assert memory_sink.calls[0]["context"] == {"project_id": "project-memory"}
    assert memory_sink.calls[0]["candidate"]["kind"] == "user_preference"
    assert memory_sink.calls[0]["candidate"]["content"] == "Keep reports local."
    assert memory_sink.calls[0]["candidate"]["applies_to"] == ["report_existing"]
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_generates_report_and_artifact() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)

    result = await service.generate_report(
        {
            "project_id": "project-2",
            "runs": [{"run_id": "run-1", "status": "completed"}],
        }
    )

    project = state_manager.get_project("project-2")
    assert result.mode == DsimWorkflowMode.report_existing
    assert result.artifacts
    assert result.artifacts[0].kind == "report"
    assert project is not None
    assert project.artifact_refs
    assert project.workflow_summaries
    assert result.artifacts[0].path.endswith(".md")
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_report_includes_persisted_diagnosis_summary() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)
    state_manager.append_run_summary(
        project_id="project-report-diagnosis",
        summary={"run_id": "run-1", "status": "failed"},
    )
    state_manager.append_workflow_summary(
        project_id="project-report-diagnosis",
        summary={
            "mode": DsimWorkflowMode.diagnose_existing.value,
            "run_id": "run-1",
            "diagnosis": {
                "category": "solver_convergence",
                "severity": "high",
                "confidence": 0.85,
                "next_actions": ["Review solver tolerance."],
            },
        },
    )

    result = await service.generate_report({"project_id": "project-report-diagnosis"})

    markdown = Path(result.artifacts[0].path).read_text(encoding="utf-8")
    assert "## Diagnosis" in markdown
    assert "solver_convergence" in markdown
    assert "Review solver tolerance." in markdown
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_runs_sweep_and_persists_summary() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)

    result = await service.run_sweep(
        {
            "project_id": "project-3",
            "combinations": [{"parameter": "alpha", "value": 1}, {"parameter": "alpha", "value": 2}],
            "confirmed": True,
        }
    )

    project = state_manager.get_project("project-3")
    assert result.mode == DsimWorkflowMode.sweep
    assert result.summary["combination_count"] == 2
    assert project is not None
    assert project.sweep_summaries
    assert result.artifacts
    assert result.artifacts[0].kind == "sweep_summary"
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_sweep_reads_curve_summary_for_each_success() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            _structured_tool_result(tool_name="UpdateDsimParameters", data={"parameters": {"alpha": 1}}),
            _structured_tool_result(tool_name="RunDsimSimulation", data={"status": "completed", "run_id": "run-1"}),
            _structured_tool_result(
                tool_name="ReadDsimCurves",
                data={"run_id": "run-1", "metrics": {"peak": 1.0}},
            ),
            _structured_tool_result(tool_name="UpdateDsimParameters", data={"parameters": {"alpha": 2}}),
            _structured_tool_result(tool_name="RunDsimSimulation", data={"status": "completed", "run_id": "run-2"}),
            _structured_tool_result(
                tool_name="ReadDsimCurves",
                data={"run_id": "run-2", "metrics": {"peak": 2.0}},
            ),
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)

    result = await service.run_sweep(
        {
            "project_id": "project-sweep",
            "handle_id": "handle-1",
            "combinations": [{"parameter": "alpha", "value": 1}, {"parameter": "alpha", "value": 2}],
            "confirmed": True,
        }
    )

    read_calls = [call for call in invoker.calls if call[0] == "mcp__dsim__ReadDsimCurves"]
    project = state_manager.get_project("project-sweep")
    assert len(read_calls) == 2
    assert result.summary["results"][0]["curve_summary"]["metrics"]["peak"] == 1.0
    assert result.summary["results"][1]["curve_summary"]["metrics"]["peak"] == 2.0
    assert project is not None
    assert [item["run_id"] for item in project.curve_summaries] == ["run-1", "run-2"]
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_single_run_uses_invoker_and_persists_summary() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker()
    service, state_manager = _build_service_with_invoker(workspace, invoker)

    result = await service.run_single(
        {
            "project_id": "project-4",
            "handle_id": "handle-1",
            "parameters": [{"name": "alpha", "value": 1}],
        }
    )

    project = state_manager.get_project("project-4")
    assert result.mode == DsimWorkflowMode.single_run
    assert invoker.calls[0][0] == "mcp__dsim__UpdateDsimParameters"
    assert invoker.calls[1][0] == "mcp__dsim__RunDsimSimulation"
    assert project is not None
    assert project.run_summaries
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_single_run_opens_project_path_without_handle() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            _structured_tool_result(
                tool_name="OpenDsimProject",
                data={"project_id": "opened-project", "handle_id": "opened-handle"},
                runtime={"project_id": "opened-project", "handle_id": "opened-handle"},
            ),
            _structured_tool_result(tool_name="RunDsimSimulation", data={"status": "completed", "run_id": "run-2"}),
            _structured_tool_result(tool_name="ReadDsimCurves", data={"run_id": "run-2", "metrics": {"peak": 2.0}}),
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)

    result = await service.run_single({"project_path": "C:/projects/model.dsim"})

    assert result.project_id == "opened-project"
    assert result.handle_id == "opened-handle"
    assert invoker.calls[0][0] == "mcp__dsim__OpenDsimProject"
    assert invoker.calls[1][0] == "mcp__dsim__RunDsimSimulation"
    assert invoker.calls[2][0] == "mcp__dsim__ReadDsimCurves"
    project = state_manager.get_project("opened-project")
    assert project is not None
    assert project.project_path == "C:/projects/model.dsim"
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_single_run_reads_curve_summary() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            _structured_tool_result(tool_name="RunDsimSimulation", data={"status": "completed", "run_id": "run-3"}),
            _structured_tool_result(
                tool_name="ReadDsimCurves",
                data={"run_id": "run-3", "metrics": {"peak": 3.0, "final_value": 1.2}},
            ),
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)

    result = await service.run_single({"project_id": "project-6", "handle_id": "handle-1"})

    assert result.summary["curve_summary"]["metrics"]["peak"] == 3.0
    assert invoker.calls[1][0] == "mcp__dsim__ReadDsimCurves"
    project = state_manager.get_project("project-6")
    assert project is not None
    assert project.curve_summaries[0]["metrics"]["peak"] == 3.0
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_demo_loop_single_run_then_report_records_state_and_artifact() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            _structured_tool_result(tool_name="UpdateDsimParameters", data={"parameters": {"alpha": 1}}),
            _structured_tool_result(
                tool_name="RunDsimSimulation",
                data={"status": "completed", "run_id": "run-demo"},
                runtime={"run_id": "run-demo"},
            ),
            _structured_tool_result(
                tool_name="ReadDsimCurves",
                data={"run_id": "run-demo", "metrics": {"peak": 4.2, "final_value": 1.7}},
                runtime={"run_id": "run-demo"},
            ),
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)

    run_result = await service.run_single(
        {
            "project_id": "project-demo",
            "handle_id": "handle-demo",
            "parameters": [{"name": "alpha", "value": 1}],
        }
    )
    report_result = await service.generate_report({"project_id": "project-demo"})

    project = state_manager.get_project("project-demo")
    assert run_result.summary["run_id"] == "run-demo"
    assert run_result.summary["curve_summary"]["metrics"]["peak"] == 4.2
    assert report_result.summary["run_count"] == 1
    assert report_result.artifacts
    assert project is not None
    assert [item["run_id"] for item in project.run_summaries] == ["run-demo"]
    assert [item["run_id"] for item in project.curve_summaries] == ["run-demo"]
    assert len(project.artifact_refs) == 1
    assert project.workflow_summaries[-1]["artifact_id"] == report_result.artifacts[0].artifact_id
    assert Path(report_result.artifacts[0].path).read_text(encoding="utf-8")
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_single_run_applies_confirmed_memory_prefill() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            _structured_tool_result(tool_name="ConfigureDsimRun", data={"configured": True}),
            _structured_tool_result(
                tool_name="RunDsimSimulation",
                data={"status": "completed", "run_id": "run-memory"},
            ),
            _structured_tool_result(
                tool_name="ReadDsimCurves",
                data={"run_id": "run-memory", "metrics": {"peak": 2.5}},
            ),
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)
    state_manager.record_memory_candidate(
        project_id="project-memory-run",
        candidate={
            "memory_id": "m-profile",
            "kind": "operating_profile",
            "content": "Use tolerance 1e-6 and max iterations 200.",
            "applies_to": ["single_run"],
            "confirmed": True,
            "priority": 5,
        },
    )

    result = await service.run_single(
        {
            "project_id": "project-memory-run",
            "handle_id": "handle-memory",
            "use_project_memory": True,
            "memory_usage_mode": "apply_prefill",
        }
    )

    assert invoker.calls[0] == (
        "mcp__dsim__ConfigureDsimRun",
        {"handle_id": "handle-memory", "config": {"tolerance": 1e-06, "max_iterations": 200}},
    )
    assert result.summary["run_plan"]["apply_mode"] == "apply_prefill"
    assert result.summary["run_plan"]["memory_hints_used"] == ["m-profile"]
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_memory_prefill_does_not_bypass_configure_permission_failure() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            ToolResult(
                content="Denied by permission policy",
                is_error=True,
                metadata={
                    "structured": {
                        "ok": False,
                        "service": "dsim",
                        "tool": "ConfigureDsimRun",
                        "data": {},
                        "runtime": {},
                        "state_updates": [],
                        "artifacts": [],
                        "error": {"code": "PERMISSION_DENIED", "message": "Denied by permission policy"},
                    }
                },
            )
        ]
    )
    service, state_manager = _build_service_with_invoker(workspace, invoker)
    state_manager.record_memory_candidate(
        project_id="project-memory-denied",
        candidate={
            "memory_id": "m-profile",
            "kind": "operating_profile",
            "content": "Use tolerance 1e-6 and max iterations 200.",
            "applies_to": ["single_run"],
            "confirmed": True,
            "priority": 5,
        },
    )

    result = await service.run_single(
        {
            "project_id": "project-memory-denied",
            "handle_id": "handle-memory",
            "use_project_memory": True,
            "memory_usage_mode": "apply_prefill",
        }
    )

    assert result.summary["ok"] is False
    assert result.summary["error"]["code"] == "PERMISSION_DENIED"
    assert [call[0] for call in invoker.calls] == ["mcp__dsim__ConfigureDsimRun"]
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_compare_runs_reads_stored_summaries() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)
    state_manager.append_run_summary(project_id="project-7", summary={"run_id": "run-1", "status": "completed"})
    state_manager.append_run_summary(project_id="project-7", summary={"run_id": "run-2", "status": "failed"})

    result = await service.compare_runs(
        {
            "project_id": "project-7",
            "runs": [{"run_id": "run-1"}, {"run_id": "run-2"}],
        }
    )

    assert result.mode == DsimWorkflowMode.report_existing
    assert result.summary["mode"] == "compare_runs"
    assert result.summary["first_status"] == "completed"
    assert result.summary["second_status"] == "failed"
    assert result.summary["status_changed"] is True
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_diagnose_uses_stored_status_and_curve_summary() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    service, state_manager = _build_service(workspace)
    state_manager.append_run_summary(
        project_id="project-8",
        summary={
            "run_id": "run-1",
            "status": "failed",
            "error": {"code": "SOLVER_FAILED", "message": "Solver diverged"},
        },
    )
    state_manager.append_curve_summary(
        project_id="project-8",
        summary={"run_id": "run-1", "metrics": {"peak": 5.0}, "empty": False},
    )

    result = await service.diagnose_existing({"project_id": "project-8", "run_id": "run-1"})

    assert result.summary["status"] == "failed"
    assert result.summary["error_code"] == "SOLVER_FAILED"
    assert result.summary["diagnosis"]["category"] == "solver_convergence"
    assert result.summary["diagnosis"]["severity"] == "high"
    assert result.summary["diagnosis"]["next_actions"]
    assert result.summary["curve_summary"]["metrics"]["peak"] == 5.0
    project = state_manager.get_project("project-8")
    assert project is not None
    assert project.workflow_summaries[-1]["diagnosis"]["category"] == "solver_convergence"
    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_workflow_service_single_run_returns_step_failure() -> None:
    workspace = Path(".test_dsim_workflow_service")
    if workspace.exists():
        shutil.rmtree(workspace)
    invoker = RecordingInvoker(
        [
            ToolResult(
                content="invalid",
                is_error=True,
                metadata={
                    "structured": {
                        "ok": False,
                        "service": "dsim",
                        "tool": "UpdateDsimParameters",
                        "error": {"code": "INVALID_PARAMETER", "message": "Invalid parameter"},
                    }
                },
            )
        ]
    )
    service, _state_manager = _build_service_with_invoker(workspace, invoker)

    result = await service.run_single(
        {
            "project_id": "project-5",
            "handle_id": "handle-1",
            "parameters": [{"name": "", "value": 1}],
        }
    )

    assert result.summary["ok"] is False
    assert result.steps[0].status == "failed"
    assert result.steps[0].error_code == "INVALID_PARAMETER"
    assert len(invoker.calls) == 1
    shutil.rmtree(workspace)
