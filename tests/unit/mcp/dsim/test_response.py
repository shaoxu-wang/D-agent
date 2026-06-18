from dsim_ai_mcp.services.dsim.response import error_response, success_response


def test_success_response_shape() -> None:
    result = success_response(
        tool="OpenDsimProject",
        workflow="OpenDsimProject",
        data={"handle_id": "h1"},
        runtime={"project_id": "p1"},
        state_updates=[{"type": "active_handle", "handle_id": "h1"}],
        artifacts=[{"kind": "summary", "path": ".dsim_agent/results/runs/r1.json"}],
        warnings=["minor warning"],
    )

    assert result == {
        "ok": True,
        "service": "dsim",
        "tool": "OpenDsimProject",
        "workflow": "OpenDsimProject",
        "data": {"handle_id": "h1"},
        "runtime": {"project_id": "p1"},
        "state_updates": [{"type": "active_handle", "handle_id": "h1"}],
        "artifacts": [{"kind": "summary", "path": ".dsim_agent/results/runs/r1.json"}],
        "warnings": ["minor warning"],
        "error": None,
    }


def test_error_response_shape() -> None:
    result = error_response(
        tool="OpenDsimProject",
        workflow="OpenDsimProject",
        code="DSIM_FILE_NOT_FOUND",
        message="File not found",
        detail={"path": "missing.dsim"},
        runtime={"project_id": "p1"},
    )

    assert result["ok"] is False
    assert result["service"] == "dsim"
    assert result["tool"] == "OpenDsimProject"
    assert result["workflow"] == "OpenDsimProject"
    assert result["data"] == {}
    assert result["runtime"] == {"project_id": "p1"}
    assert result["state_updates"] == []
    assert result["artifacts"] == []
    assert result["warnings"] == []
    assert result["error"] == {
        "code": "DSIM_FILE_NOT_FOUND",
        "message": "File not found",
        "detail": {"path": "missing.dsim"},
    }
