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
