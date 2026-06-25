import shutil
from pathlib import Path

from cc.dsim.memory_sink import DeferredMemorySink
from cc.dsim.state import DsimProjectStateManager


def test_deferred_memory_sink_marks_confirmed_candidate_deferred() -> None:
    workspace = Path(".test_dsim_memory_sink")
    if workspace.exists():
        shutil.rmtree(workspace)
    manager = DsimProjectStateManager(workspace=workspace, session_id="session-1")
    sink = DeferredMemorySink(state_manager=manager)

    try:
        payload = sink.save_confirmed(
            candidate={
                "kind": "conclusion",
                "evidence_refs": [{"source": "SaveProjectContext", "project_id": "project-1"}],
                "confirmed": True,
            },
            context={"project_id": "project-1"},
        )

        project = manager.get_project("project-1")
        assert payload["long_term_memory_status"] == "deferred"
        assert project is not None
        assert project.memory_candidates == [payload]
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)
