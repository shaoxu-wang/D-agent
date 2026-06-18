import json

import pytest

from cc.mcp.client import McpToolProxy


class TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class ToolResultLike:
    def __init__(self, content) -> None:
        self.content = content


class FakeSession:
    async def call_tool(self, tool_name: str, arguments: dict):
        payload = {
            "ok": True,
            "service": "dsim",
            "tool": tool_name,
            "workflow": "OpenDsimProject",
            "data": {"handle_id": "h1"},
            "runtime": {},
            "state_updates": [{"type": "active_handle", "handle_id": "h1"}],
            "artifacts": [],
            "warnings": [],
            "error": None,
        }
        return ToolResultLike([TextBlock(json.dumps(payload))])


@pytest.mark.asyncio
async def test_mcp_proxy_preserves_structured_dsim_response() -> None:
    proxy = McpToolProxy(
        server_name="dsim",
        tool_name="OpenDsimProject",
        description="",
        input_schema={"type": "object"},
        session=FakeSession(),
    )

    result = await proxy.execute({"path": "demo.dsim"})

    assert "OpenDsimProject" in result.text
    assert result.metadata["structured"]["state_updates"] == [{"type": "active_handle", "handle_id": "h1"}]
    assert result.metadata["mcp"] == {"server_name": "dsim", "tool_name": "OpenDsimProject"}


def test_dsim_mcp_proxy_is_not_concurrency_safe() -> None:
    proxy = McpToolProxy(
        server_name="dsim",
        tool_name="RunDsimSimulation",
        description="",
        input_schema={"type": "object"},
        session=FakeSession(),
    )

    assert proxy.is_concurrency_safe({}) is False


def test_non_dsim_mcp_proxy_remains_concurrency_safe() -> None:
    proxy = McpToolProxy(
        server_name="other",
        tool_name="Lookup",
        description="",
        input_schema={"type": "object"},
        session=FakeSession(),
    )

    assert proxy.is_concurrency_safe({}) is True
