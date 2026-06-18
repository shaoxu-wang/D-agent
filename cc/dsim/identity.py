"""DSim identity helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_project_path(path: str | Path) -> str:
    """Return an absolute resolved project path."""
    return str(Path(path).expanduser().resolve())


def build_project_id(path: str | Path) -> str:
    """Build a stable project id from the normalized project path."""
    normalized = normalize_project_path(path)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"project-{digest}"
