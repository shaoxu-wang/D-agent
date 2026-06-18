import shutil
from pathlib import Path

from cc.dsim.storage import read_json_file, write_json_file_atomic


def _workspace_tmp(name: str) -> Path:
    root = Path(".test_dsim_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_atomic_json_write_and_read() -> None:
    tmp_path = _workspace_tmp("storage")
    target = tmp_path / "state.json"

    write_json_file_atomic(target, {"schema_version": 1, "value": "ok"})

    assert read_json_file(target) == {"schema_version": 1, "value": "ok"}
    assert not list(tmp_path.glob("*.tmp"))

    shutil.rmtree(tmp_path)
