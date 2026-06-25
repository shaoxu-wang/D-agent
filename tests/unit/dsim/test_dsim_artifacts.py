import shutil
from pathlib import Path

from cc.dsim.artifacts import DsimArtifactStore


def test_artifact_store_writes_report_and_sweep_summary() -> None:
    workspace = Path(".test_dsim_artifacts")
    if workspace.exists():
        shutil.rmtree(workspace)
    store = DsimArtifactStore(workspace=workspace)

    report_ref = store.write_report(project_id="project-1", markdown="# Report\n")
    sweep_ref = store.write_sweep_summary(project_id="project-1", summary={"ok": True})

    assert report_ref["kind"] == "report"
    assert report_ref["mime_type"] == "text/markdown"
    assert report_ref["storage_key"].startswith("local/reports/")
    assert "uri" in report_ref
    assert Path(report_ref["path"]).is_file()
    assert sweep_ref["kind"] == "sweep_summary"
    assert sweep_ref["mime_type"] == "application/json"
    assert sweep_ref["storage_key"].startswith("local/sweeps/")
    assert "uri" in sweep_ref
    assert Path(sweep_ref["path"]).is_file()

    shutil.rmtree(workspace)
