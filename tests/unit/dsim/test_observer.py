from cc.dsim.observer import DsimToolResultObserver
from cc.tools.base import ToolResult


class FakeStateManager:
    def __init__(self) -> None:
        self.events = []

    def apply_state_events(self, events):
        self.events.extend(events)


class FakeAuditLogger:
    def __init__(self) -> None:
        self.entries = []

    def write_entry(self, entry):
        self.entries.append(entry)


def test_observer_applies_structured_dsim_result_once() -> None:
    state = FakeStateManager()
    audit = FakeAuditLogger()
    observer = DsimToolResultObserver(state_manager=state, audit_logger=audit)
    result = ToolResult(
        content="DSim OpenDsimProject returned ok=True",
        metadata={
            "structured": {
                "ok": True,
                "service": "dsim",
                "tool": "OpenDsimProject",
                "state_updates": [{"type": "active_handle", "handle_id": "h1"}],
                "artifacts": [],
                "error": None,
            }
        },
    )

    observer.observe(
        tool_call_id="toolu_1",
        tool_name="mcp__dsim__OpenDsimProject",
        tool_input={"path": "demo.dsim"},
        result=result,
        permission_record=None,
        duration_ms=10,
    )

    assert state.events == [{"type": "active_handle", "handle_id": "h1"}]
    assert audit.entries[0]["tool_call_id"] == "toolu_1"


def test_observer_ignores_content_when_structured_metadata_exists() -> None:
    state = FakeStateManager()
    audit = FakeAuditLogger()
    observer = DsimToolResultObserver(state_manager=state, audit_logger=audit)
    result = ToolResult(
        content='{"service": "dsim", "state_updates": [{"type": "active_handle", "handle_id": "wrong"}]}',
        metadata={
            "structured": {
                "ok": True,
                "service": "dsim",
                "tool": "OpenDsimProject",
                "state_updates": [{"type": "active_handle", "handle_id": "right"}],
                "artifacts": [],
                "error": None,
            }
        },
    )

    observer.observe(
        tool_call_id="toolu_2",
        tool_name="mcp__dsim__OpenDsimProject",
        tool_input={"path": "demo.dsim"},
        result=result,
        permission_record=None,
        duration_ms=10,
    )

    assert state.events == [{"type": "active_handle", "handle_id": "right"}]
