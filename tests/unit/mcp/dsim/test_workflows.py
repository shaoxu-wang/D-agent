import shutil
from pathlib import Path
from uuid import uuid4

from dsim_ai_mcp.services.dsim import workflows


def _workspace_tmp() -> Path:
    root = Path(".test_workflows_tmp") / uuid4().hex
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def _assert_stage_2b_envelope(result: dict) -> None:
    assert set(["ok", "service", "tool", "data", "error", "runtime", "artifacts"]).issubset(result)
    assert result["service"] == "dsim"
    assert isinstance(result["data"], dict)
    assert isinstance(result["runtime"], dict)
    assert set(["client_id", "session_id", "project_id", "handle_id", "run_id"]).issubset(result["runtime"])
    assert isinstance(result["artifacts"], list)
    if result["ok"]:
        assert result["error"] is None
    else:
        assert result["error"]["code"]
        assert result["error"]["message"]
        assert "details" in result["error"]


def test_validate_environment_reports_mock_backend() -> None:
    result = workflows.ValidateDsimEnvironment()

    _assert_stage_2b_envelope(result)
    assert result["ok"] is True
    assert result["data"]["backend"] == "mock"
    assert result["data"]["real_api_available"] is False


def test_open_project_creates_handle_and_state_update() -> None:
    root = _workspace_tmp()
    try:
        result = workflows.OpenDsimProject(path=str(root / "demo.dsim"), project_id="project-1")

        _assert_stage_2b_envelope(result)
        assert result["ok"] is True
        assert result["runtime"]["project_id"] == "project-1"
        assert result["data"]["handle_id"].startswith("mock-handle-")
        assert any(
            update["type"] == "active_project" and update["project_id"] == "project-1"
            for update in result["state_updates"]
        )
    finally:
        shutil.rmtree(root)


def test_run_simulation_can_timeout() -> None:
    root = _workspace_tmp()
    try:
        opened = workflows.OpenDsimProject(path=str(root / "demo.dsim"), project_id="project-timeout")

        result = workflows.RunDsimSimulation(handle_id=opened["data"]["handle_id"], timeout_seconds=0)

        _assert_stage_2b_envelope(result)
        assert result["ok"] is False
        assert result["error"]["code"] == "SIMULATION_TIMEOUT"
        assert result["data"]["status"] == "timeout"
    finally:
        shutil.rmtree(root)


def test_update_parameters_is_fail_fast() -> None:
    root = _workspace_tmp()
    try:
        opened = workflows.OpenDsimProject(path=str(root / "demo.dsim"), project_id="project-param")

        result = workflows.UpdateDsimParameters(
            handle_id=opened["data"]["handle_id"],
            parameters=[{"name": "", "value": 1}],
        )

        _assert_stage_2b_envelope(result)
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PARAMETER"
    finally:
        shutil.rmtree(root)
