"""Tests for MCP configuration loading.

Verifies T8.1: Config parsing from settings.json and .mcp.json.
"""

import json
import shutil
from pathlib import Path

from cc.mcp.config import load_mcp_configs


def _workspace_tmp(name: str) -> Path:
    root = Path(".test_mcp_config_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


class TestMcpConfig:
    def test_load_from_mcp_json(self) -> None:
        tmp_path = _workspace_tmp("mcp_json")
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                }
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json))
        configs = load_mcp_configs(str(tmp_path))
        assert len(configs) == 1
        assert configs[0].name == "filesystem"
        assert configs[0].transport == "stdio"
        assert configs[0].command == "npx"
        shutil.rmtree(tmp_path)

    def test_load_from_settings(self) -> None:
        tmp_path = _workspace_tmp("settings")
        settings = {
            "mcpServers": {
                "myserver": {
                    "type": "sse",
                    "url": "http://localhost:3000/sse",
                }
            }
        }
        (tmp_path / "settings.json").write_text(json.dumps(settings))
        configs = load_mcp_configs(str(tmp_path / "project"), claude_dir=tmp_path)
        assert len(configs) == 1
        assert configs[0].transport == "sse"
        assert configs[0].url == "http://localhost:3000/sse"
        shutil.rmtree(tmp_path)

    def test_skip_unknown_transport(self) -> None:
        tmp_path = _workspace_tmp("unknown_transport")
        mcp_json = {
            "mcpServers": {
                "weird": {"type": "ftp", "url": "ftp://server"},
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json))
        configs = load_mcp_configs(str(tmp_path))
        assert len(configs) == 0
        shutil.rmtree(tmp_path)

    def test_missing_command_for_stdio(self) -> None:
        tmp_path = _workspace_tmp("missing_command")
        mcp_json = {"mcpServers": {"bad": {"type": "stdio"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json))
        configs = load_mcp_configs(str(tmp_path))
        assert len(configs) == 0
        shutil.rmtree(tmp_path)

    def test_no_config_files(self) -> None:
        tmp_path = _workspace_tmp("no_config")
        configs = load_mcp_configs(str(tmp_path), claude_dir=tmp_path)
        assert configs == []
        shutil.rmtree(tmp_path)

    def test_env_vars_passed(self) -> None:
        tmp_path = _workspace_tmp("env_vars")
        mcp_json = {
            "mcpServers": {
                "server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                    "env": {"API_KEY": "secret"},
                }
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json))
        configs = load_mcp_configs(str(tmp_path))
        assert configs[0].env == {"API_KEY": "secret"}
        shutil.rmtree(tmp_path)
