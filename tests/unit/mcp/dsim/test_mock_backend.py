import shutil
from pathlib import Path
from uuid import uuid4

from dsim_ai_mcp.services.dsim.mock_backend import MockDsimBackend


def _workspace_tmp() -> Path:
    root = Path(".test_mock_backend_tmp") / uuid4().hex
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_mock_backend_opens_project_and_returns_snapshot() -> None:
    root = _workspace_tmp()
    try:
        backend = MockDsimBackend()

        opened = backend.open_project(path=str(root / "demo.dsim"), project_id="project-1")
        snapshot = backend.get_snapshot(opened.handle_id)

        assert opened.handle_id.startswith("mock-handle-")
        assert snapshot["project_id"] == "project-1"
        assert snapshot["path"].endswith("demo.dsim")
    finally:
        shutil.rmtree(root)


def test_mock_backend_fails_invalid_parameter_update() -> None:
    root = _workspace_tmp()
    try:
        backend = MockDsimBackend()
        opened = backend.open_project(path=str(root / "demo.dsim"), project_id="project-1")

        result = backend.update_parameters(opened.handle_id, [{"name": "", "value": 1}])

        assert result.ok is False
        assert result.error_code == "INVALID_PARAMETER"
    finally:
        shutil.rmtree(root)


def test_mock_backend_runs_success_and_empty_curve_case() -> None:
    root = _workspace_tmp()
    try:
        backend = MockDsimBackend()
        opened = backend.open_project(path=str(root / "empty_curve_demo.dsim"), project_id="project-1")

        run = backend.run_simulation(opened.handle_id, timeout_seconds=1800)
        curves = backend.read_curves(opened.handle_id, mode="summary", artifact_root=None)

        assert run.ok is True
        assert run.data["status"] == "completed"
        assert curves.ok is True
        assert curves.data["curves"] == []
    finally:
        shutil.rmtree(root)


def test_mock_backend_returns_stage_2a_curve_metrics() -> None:
    root = _workspace_tmp()
    try:
        backend = MockDsimBackend()
        opened = backend.open_project(path=str(root / "demo.dsim"), project_id="project-1")
        backend.update_parameters(opened.handle_id, [{"name": "alpha", "value": 2}])

        curves = backend.read_curves(opened.handle_id, mode="summary", artifact_root=None)

        curve = curves.data["curves"][0]
        assert curve["peak"] == 2.0
        assert curve["final_value"] == 1.0
        assert curve["settling_hint"] == "stable"
    finally:
        shutil.rmtree(root)


def test_mock_backend_returns_stage_2a_failure_signals() -> None:
    root = _workspace_tmp()
    try:
        backend = MockDsimBackend()
        opened = backend.open_project(path=str(root / "demo.dsim"), project_id="project-1")
        backend.update_parameters(opened.handle_id, [{"name": "force_failure", "value": True}])

        run = backend.run_simulation(opened.handle_id, timeout_seconds=1800)

        assert run.ok is False
        assert run.data["signal"] == "solver_failed"
        assert run.error_code == "SIMULATION_FAILED"
    finally:
        shutil.rmtree(root)
