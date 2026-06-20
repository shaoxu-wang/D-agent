import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from dsim_ai_mcp.services.dsim.artifacts import ArtifactPathError, resolve_artifact_path


def _workspace_tmp() -> Path:
    root = Path(".test_artifacts_tmp") / uuid4().hex
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_resolve_artifact_path_accepts_subpath_under_approved_root() -> None:
    root = _workspace_tmp()
    approved = root / "workspace" / ".dsim_agent" / "results"
    approved.mkdir(parents=True)

    try:
        result = resolve_artifact_path(
            artifact_root=str(approved),
            relative_path="curves/run-1.json",
            approved_roots=[approved],
        )

        assert result == (approved / "curves" / "run-1.json").resolve()
    finally:
        shutil.rmtree(root)


def test_resolve_artifact_path_rejects_unapproved_root() -> None:
    root = _workspace_tmp()
    approved = root / "approved"
    unapproved = root / "unapproved"
    approved.mkdir()
    unapproved.mkdir()

    try:
        with pytest.raises(ArtifactPathError, match="outside approved artifact roots"):
            resolve_artifact_path(
                artifact_root=str(unapproved),
                relative_path="curves/run-1.json",
                approved_roots=[approved],
            )
    finally:
        shutil.rmtree(root)


def test_resolve_artifact_path_rejects_path_traversal() -> None:
    root = _workspace_tmp()
    approved = root / "approved"
    approved.mkdir()

    try:
        with pytest.raises(ArtifactPathError, match="outside approved artifact roots"):
            resolve_artifact_path(
                artifact_root=str(approved),
                relative_path="../escape.json",
                approved_roots=[approved],
            )
    finally:
        shutil.rmtree(root)
