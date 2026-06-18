"""DSim audit logging."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cc.dsim.paths import DsimPaths


class DsimAuditLogger:
    """Append-only JSONL audit logger for DSim tool calls."""

    def __init__(self, *, workspace: str | Path) -> None:
        self.paths = DsimPaths(workspace)
        self.paths.ensure()

    def write_entry(self, entry: dict[str, Any]) -> None:
        """Append an audit entry to the current UTC date log."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        target = self.paths.audit / f"{date}.jsonl"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
