import shutil
from pathlib import Path

from cc.dsim.memory_context import MemoryContextBuilder
from cc.dsim.state import DsimProjectStateManager


def test_memory_context_uses_confirmed_candidates_by_priority() -> None:
    workspace = Path(".test_dsim_memory_context")
    if workspace.exists():
        shutil.rmtree(workspace)
    state = DsimProjectStateManager(workspace=workspace, session_id="session-1")
    state.record_memory_candidate(
        project_id="project-memory",
        candidate={
            "memory_id": "m-low",
            "kind": "project_fact",
            "content": "Use default solver settings.",
            "applies_to": ["single_run"],
            "confirmed": True,
            "priority": 1,
        },
    )
    state.record_memory_candidate(
        project_id="project-memory",
        candidate={
            "memory_id": "m-high",
            "kind": "operating_profile",
            "content": "Prefer tolerance 1e-6 for this project.",
            "applies_to": ["single_run"],
            "confirmed": True,
            "priority": 5,
        },
    )
    state.record_memory_candidate(
        project_id="project-memory",
        candidate={
            "memory_id": "m-other",
            "kind": "project_caution",
            "content": "Sweep runs are slow.",
            "applies_to": ["sweep"],
            "confirmed": True,
            "priority": 9,
        },
    )
    state.record_memory_candidate(
        project_id="project-memory",
        candidate={
            "memory_id": "m-unconfirmed",
            "kind": "diagnostic_hint",
            "content": "Ignore unconfirmed hint.",
            "applies_to": ["single_run"],
            "confirmed": False,
            "priority": 10,
        },
    )

    context = MemoryContextBuilder(reader=state).build(project_id="project-memory", applies_to="single_run")

    assert [item.memory_id for item in context.memories] == ["m-high", "m-low"]
    assert context.compact()["memories"][0]["kind"] == "operating_profile"
    assert context.warnings == []

    shutil.rmtree(workspace)


def test_memory_context_warns_when_project_has_no_confirmed_memory() -> None:
    workspace = Path(".test_dsim_memory_context")
    if workspace.exists():
        shutil.rmtree(workspace)
    state = DsimProjectStateManager(workspace=workspace, session_id="session-1")

    context = MemoryContextBuilder(reader=state).build(project_id="missing-project", applies_to="single_run")

    assert context.memories == []
    assert context.warnings == ["No confirmed project memory found for missing-project."]

    shutil.rmtree(workspace)
