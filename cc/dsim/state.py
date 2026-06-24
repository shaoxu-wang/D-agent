"""DSim project state manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.models import ActiveDsimContext, DsimProject
from cc.dsim.paths import DsimPaths
from cc.dsim.storage import read_json_file, write_json_file_atomic

if TYPE_CHECKING:
    from pathlib import Path


class DsimProjectStateManager:
    """Persist and update workspace-local DSim project/session state."""

    def __init__(self, *, workspace: str | Path, session_id: str, client_id: str = "local") -> None:
        self.paths = DsimPaths(workspace)
        self.paths.ensure()
        self.session_id = session_id
        self.client_id = client_id

    def set_active_context(
        self,
        *,
        project_id: str,
        handle_id: str | None,
        run_id: str | None,
    ) -> None:
        """Persist the session's active DSim context."""
        context = ActiveDsimContext(
            client_id=self.client_id,
            session_id=self.session_id,
            active_project_id=project_id,
            active_handle_id=handle_id,
            active_run_id=run_id,
        )
        write_json_file_atomic(self.paths.sessions / f"{self.session_id}.json", context.model_dump())
        self._merge_project_index(project_id)

    def get_active_context(self) -> ActiveDsimContext | None:
        """Return the current session's active DSim context."""
        data = self._read_json(self.paths.sessions / f"{self.session_id}.json")
        if not data:
            return None
        return ActiveDsimContext(**data)

    def upsert_project(self, *, project_id: str, project_path: str) -> None:
        """Create or update a project record without dropping accumulated summaries."""
        project = self._load_or_create_project(project_id)
        project.project_path = project_path

        write_json_file_atomic(self.paths.projects / f"{project_id}.json", project.model_dump())
        self._merge_project_index(project_id)

    def get_project(self, project_id: str) -> DsimProject | None:
        """Return a persisted project by id."""
        data = self._read_json(self.paths.projects / f"{project_id}.json")
        if not data:
            return None
        return self._project_from_data(data, project_id)

    def apply_state_events(self, events: list[dict[str, Any]]) -> None:
        """Apply normalized DSim state events from tool result adapters."""
        for event in events:
            event_type = event.get("type")
            if event_type == "active_project":
                project_id = str(event["project_id"])
                self.set_active_context(project_id=project_id, handle_id=None, run_id=None)
                self.upsert_project(project_id=project_id, project_path=str(event.get("path", "")))
            elif event_type == "active_handle":
                self.set_active_context(
                    project_id=str(event["project_id"]),
                    handle_id=_optional_str(event.get("handle_id")),
                    run_id=None,
                )
            elif event_type == "run_finished":
                session = self._read_json(self.paths.sessions / f"{self.session_id}.json")
                active_project_id = session.get("active_project_id")
                if active_project_id:
                    self.set_active_context(
                        project_id=str(active_project_id),
                        handle_id=_optional_str(event.get("handle_id")),
                        run_id=_optional_str(event.get("run_id")),
                    )

    def append_run_summary(self, *, project_id: str, summary: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.run_summaries.append(summary)
        self._write_project(project)

    def append_curve_summary(self, *, project_id: str, summary: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.curve_summaries.append(summary)
        self._write_project(project)

    def get_curve_summary(self, project_id: str, run_id: str) -> dict[str, Any] | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for summary in project.curve_summaries:
            if summary.get("run_id") == run_id:
                return summary
        return None

    def list_curve_summaries(self, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        return [] if project is None else list(project.curve_summaries)

    def get_run_summary(self, project_id: str, run_id: str) -> dict[str, Any] | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for summary in project.run_summaries:
            if summary.get("run_id") == run_id:
                return summary
        return None

    def list_run_summaries(self, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        return [] if project is None else list(project.run_summaries)

    def append_workflow_summary(self, *, project_id: str, summary: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.workflow_summaries.append(summary)
        self._write_project(project)

    def append_sweep_summary(self, *, project_id: str, summary: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.sweep_summaries.append(summary)
        self._write_project(project)

    def add_artifact_ref(self, *, project_id: str, artifact_ref: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.artifact_refs.append(artifact_ref)
        self._write_project(project)

    def record_memory_candidate(self, *, project_id: str, candidate: dict[str, Any]) -> None:
        project = self._load_or_create_project(project_id)
        project.memory_candidates.append(candidate)
        self._write_project(project)

    def _merge_project_index(self, project_id: str) -> None:
        index_path = self.paths.root / "project_state.json"
        index = self._read_json(index_path)
        projects = set(index.get("projects", []))
        projects.add(project_id)
        write_json_file_atomic(index_path, {"schema_version": 1, "projects": sorted(projects)})

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return read_json_file(path)

    def _load_or_create_project(self, project_id: str) -> DsimProject:
        existing = self._read_json(self.paths.projects / f"{project_id}.json")
        if existing:
            return self._project_from_data(existing, project_id)
        return DsimProject(project_id=project_id, project_path="")

    def _write_project(self, project: DsimProject) -> None:
        write_json_file_atomic(self.paths.projects / f"{project.project_id}.json", project.model_dump())

    def _project_from_data(self, data: dict[str, Any], project_id: str) -> DsimProject:
        normalized = dict(data)
        normalized["project_id"] = project_id
        if "artifact_refs" not in normalized and "artifacts" in normalized:
            normalized["artifact_refs"] = list(normalized.get("artifacts", []))
        normalized.pop("artifacts", None)
        normalized.setdefault("workflow_summaries", [])
        normalized.setdefault("sweep_summaries", [])
        normalized.setdefault("artifact_refs", [])
        normalized.setdefault("memory_candidates", [])
        normalized.setdefault("run_summaries", [])
        normalized.setdefault("curve_summaries", [])
        return DsimProject(**normalized)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
