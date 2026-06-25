"""Local artifact store for DSim workflow outputs."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import uuid4

from cc.dsim.paths import DsimPaths

if TYPE_CHECKING:
    from pathlib import Path


class DsimArtifactStore:
    """Write DSim workflow artifacts under the local workspace."""

    def __init__(self, *, workspace: str | Path) -> None:
        self.paths = DsimPaths(workspace)
        self.paths.ensure()

    def write_report(self, *, project_id: str, markdown: str) -> dict[str, str]:
        report_id = f"report-{uuid4().hex[:8]}"
        path = self.paths.reports / f"{report_id}.md"
        path.write_text(markdown, encoding="utf-8")
        return self._ref(report_id, "report", f"local/reports/{report_id}.md", path, "text/markdown")

    def write_sweep_summary(self, *, project_id: str, summary: dict[str, object]) -> dict[str, str]:
        sweep_id = f"sweep-{uuid4().hex[:8]}"
        path = self.paths.sweeps / f"{sweep_id}.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._ref(sweep_id, "sweep_summary", f"local/sweeps/{sweep_id}.json", path, "application/json")

    def _ref(self, artifact_id: str, kind: str, storage_key: str, path: Path, mime_type: str) -> dict[str, str]:
        return {
            "artifact_id": artifact_id,
            "kind": kind,
            "path": str(path.resolve()),
            "storage_key": storage_key,
            "uri": "",
            "mime_type": mime_type,
        }
