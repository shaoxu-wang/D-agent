from dsim_ai_mcp.services.dsim.mock_backend import MockDsimBackend
from dsim_ai_mcp.services.dsim.runtime import DsimRuntime, HandleRegistry


def test_handle_registry_tracks_metadata() -> None:
    registry = HandleRegistry()
    handle_id = registry.create(
        handle={"native": "handle"},
        project_id="project-1",
        client_id="local",
        session_id="session-1",
    )

    record = registry.get(handle_id)

    assert record.handle == {"native": "handle"}
    assert record.project_id == "project-1"
    assert record.client_id == "local"
    assert record.session_id == "session-1"
    assert record.closed is False


def test_close_marks_handle_closed() -> None:
    registry = HandleRegistry()
    handle_id = registry.create(handle=object(), project_id="p", client_id="c", session_id="s")

    registry.close(handle_id)

    assert registry.get(handle_id).closed is True


def test_close_session_closes_all_session_handles() -> None:
    registry = HandleRegistry()
    first = registry.create(handle=object(), project_id="p1", client_id="c", session_id="s")
    second = registry.create(handle=object(), project_id="p2", client_id="c", session_id="s")
    third = registry.create(handle=object(), project_id="p3", client_id="c", session_id="other")

    registry.close_session("s")

    assert registry.get(first).closed is True
    assert registry.get(second).closed is True
    assert registry.get(third).closed is False


def test_runtime_uses_thread_lock_and_mock_backend() -> None:
    runtime = DsimRuntime()

    assert isinstance(runtime.backend, MockDsimBackend)
    with runtime.lock:
        handle_id = runtime.handles.create(handle={"mock": True}, project_id="p", client_id="c", session_id="s")

    assert runtime.handles.get(handle_id).project_id == "p"
