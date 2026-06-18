from cc.dsim.result_adapter import DsimResultAdapter


def test_adapter_builds_state_events_and_summary() -> None:
    adapter = DsimResultAdapter()
    payload = {
        "ok": True,
        "service": "dsim",
        "tool": "OpenDsimProject",
        "state_updates": [{"type": "active_handle", "handle_id": "h1"}],
        "artifacts": [{"kind": "summary", "path": "runs/r1.json"}],
        "error": None,
    }

    adapted = adapter.adapt(payload)

    assert adapted.state_events == [{"type": "active_handle", "handle_id": "h1"}]
    assert adapted.artifacts == [{"kind": "summary", "path": "runs/r1.json"}]
    assert adapted.result_summary == {"ok": True, "tool": "OpenDsimProject", "error": None}
