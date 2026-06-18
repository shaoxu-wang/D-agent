import pytest

from cc.main import _connect_mcp_servers
from cc.tools.base import ToolRegistry


@pytest.mark.asyncio
async def test_connect_mcp_servers_registers_dynamic_dsim_tools(monkeypatch) -> None:
    calls = []

    def fake_load_mcp_configs(_cwd: str):
        return []

    async def fake_connect_mcp_server(_config, _registry):
        raise AssertionError("no configs should be connected")

    def fake_register_dsim_tools(registry: ToolRegistry):
        calls.append(registry)

    monkeypatch.setattr("cc.mcp.config.load_mcp_configs", fake_load_mcp_configs)
    monkeypatch.setattr("cc.mcp.client.connect_mcp_server", fake_connect_mcp_server)
    monkeypatch.setattr("cc.dsim.registry.register_dsim_tools", fake_register_dsim_tools)

    registry = ToolRegistry()
    await _connect_mcp_servers("workspace", registry)

    assert calls == [registry]
