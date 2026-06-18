import shutil
from pathlib import Path

from cc.dsim.identity import build_project_id, normalize_project_path


def _workspace_tmp(name: str) -> Path:
    root = Path(".test_dsim_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_normalize_project_path_uses_absolute_resolved_path() -> None:
    tmp_path = _workspace_tmp("identity_normalize")
    project = tmp_path / "demo.dsim"
    project.write_text("content", encoding="utf-8")

    assert normalize_project_path(project) == str(project.resolve())

    shutil.rmtree(tmp_path)


def test_project_id_is_stable_for_same_path() -> None:
    tmp_path = _workspace_tmp("identity_project_id")
    project = tmp_path / "demo.dsim"
    project.write_text("v1", encoding="utf-8")

    first = build_project_id(project)
    project.write_text("v2", encoding="utf-8")
    second = build_project_id(project)

    assert first == second
    assert first.startswith("project-")

    shutil.rmtree(tmp_path)
