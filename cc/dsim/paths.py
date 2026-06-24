"""Local DSim Agent paths."""

from __future__ import annotations

from pathlib import Path


class DsimPaths:
    """Workspace-local paths for DSim state, audit, and artifacts."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.root = self.workspace / ".dsim_agent"
        self.sessions = self.root / "sessions"
        self.projects = self.root / "projects"
        self.audit = self.root / "audit"
        self.results = self.root / "results"
        self.reports = self.root / "reports"
        self.sweeps = self.results / "sweeps"

    def ensure(self) -> None:
        """Create the DSim local state directory tree."""
        for path in [self.root, self.sessions, self.projects, self.audit, self.results, self.reports, self.sweeps]:
            path.mkdir(parents=True, exist_ok=True)
