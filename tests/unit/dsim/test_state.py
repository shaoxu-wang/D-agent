import shutil
from pathlib import Path

from cc.dsim.state import DsimProjectStateManager


def _workspace_tmp(name: str) -> Path:
    root = Path(".test_dsim_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_state_manager_writes_session_and_project_files() -> None:
    tmp_path = _workspace_tmp("state_files")
    manager = DsimProjectStateManager(workspace=tmp_path, session_id="session-1")

    manager.set_active_context(project_id="project-1", handle_id="handle-1", run_id="run-1")
    manager.upsert_project(project_id="project-1", project_path=str(tmp_path / "demo.dsim"))

    assert (tmp_path / ".dsim_agent" / "sessions" / "session-1.json").is_file()
    assert (tmp_path / ".dsim_agent" / "projects" / "project-1.json").is_file()
    assert (tmp_path / ".dsim_agent" / "project_state.json").is_file()

    shutil.rmtree(tmp_path)


def test_state_manager_applies_state_events_without_overwriting_project_index() -> None:
    tmp_path = _workspace_tmp("state_events")
    manager = DsimProjectStateManager(workspace=tmp_path, session_id="session-1")

    manager.upsert_project(project_id="project-1", project_path=str(tmp_path / "one.dsim"))
    manager.upsert_project(project_id="project-2", project_path=str(tmp_path / "two.dsim"))
    manager.apply_state_events(
        [
            {"type": "active_project", "project_id": "project-1", "path": str(tmp_path / "one.dsim")},
            {"type": "active_handle", "handle_id": "handle-1", "project_id": "project-1"},
            {"type": "run_finished", "handle_id": "handle-1", "run_id": "run-1", "status": "completed"},
        ]
    )

    index = (tmp_path / ".dsim_agent" / "project_state.json").read_text(encoding="utf-8")
    assert "project-1" in index
    assert "project-2" in index

    shutil.rmtree(tmp_path)


def test_state_manager_exposes_active_context_and_project() -> None:
    tmp_path = _workspace_tmp("state_access")
    manager = DsimProjectStateManager(workspace=tmp_path, session_id="session-1")

    manager.set_active_context(project_id="project-1", handle_id="handle-1", run_id="run-1")
    manager.upsert_project(project_id="project-1", project_path=str(tmp_path / "demo.dsim"))

    active = manager.get_active_context()
    project = manager.get_project("project-1")

    assert active is not None
    assert active.active_project_id == "project-1"
    assert project is not None
    assert project.project_id == "project-1"

    shutil.rmtree(tmp_path)


def test_state_manager_exposes_curve_summaries() -> None:
    tmp_path = _workspace_tmp("curve_access")
    manager = DsimProjectStateManager(workspace=tmp_path, session_id="session-1")

    manager.append_curve_summary(project_id="project-1", summary={"run_id": "run-1", "metrics": {"peak": 2.0}})

    assert manager.get_curve_summary("project-1", "run-1") == {"run_id": "run-1", "metrics": {"peak": 2.0}}
    assert manager.list_curve_summaries("project-1") == [{"run_id": "run-1", "metrics": {"peak": 2.0}}]

    shutil.rmtree(tmp_path)
