"""JSON storage helpers for local DSim Agent state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_json_file(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON object atomically using a same-directory temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)
