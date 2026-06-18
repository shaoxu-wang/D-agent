import json
import shutil
from pathlib import Path

from cc.dsim.audit import DsimAuditLogger


def _workspace_tmp(name: str) -> Path:
    root = Path(".test_dsim_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_audit_logger_writes_jsonl() -> None:
    tmp_path = _workspace_tmp("audit")
    logger = DsimAuditLogger(workspace=tmp_path)

    logger.write_entry(
        {
            "tool_call_id": "toolu_1",
            "client_id": "local",
            "session_id": "session-1",
            "project_id": "project-1",
            "tool_name": "mcp__dsim__OpenDsimProject",
            "risk_level": "ask",
            "permission_decision": "allow",
            "input_summary": "path=demo.dsim",
            "result_summary": "opened project",
            "ok": True,
            "error": None,
            "duration_ms": 12,
            "timestamp": "2026-06-18T00:00:00+00:00",
        }
    )

    files = list((tmp_path / ".dsim_agent" / "audit").glob("*.jsonl"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8").strip())["tool_call_id"] == "toolu_1"

    shutil.rmtree(tmp_path)
