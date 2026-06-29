from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest

from cc.dsim.runtime import build_dsim_runtime
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeOpenProjectTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        project_path = str(tool_input["path"])
        return ToolResult(
            content="opened",
            metadata={
                "structured": {
                    "ok": True,
                    "service": "dsim",
                    "tool": "OpenDsimProject",
                    "runtime": {"project_id": "project-runtime"},
                    "state_updates": [
                        {
                            "type": "active_project",
                            "project_id": "project-runtime",
                            "path": project_path,
                        }
                    ],
                    "artifacts": [],
                    "error": None,
                }
            },
        )


@pytest.mark.asyncio
async def test_runtime_invoker_wires_observer_to_state_and_audit() -> None:
    workspace = Path(".tmp") / "test-runtime-wiring" / uuid4().hex
    registry = ToolRegistry()
    registry.register(FakeOpenProjectTool())
    project_path = workspace / "demo.dsim"

    try:
        runtime = build_dsim_runtime(
            workspace=str(workspace),
            session_id="session-runtime",
            permission_ctx=None,
            registry=registry,
        )

        result = await runtime.invoker.call("mcp__dsim__OpenDsimProject", {"path": str(project_path)})

        assert result.is_error is False
        context = runtime.state_manager.get_active_context()
        assert context is not None
        assert context.active_project_id == "project-runtime"
        project = runtime.state_manager.get_project("project-runtime")
        assert project is not None
        assert project.project_path == str(project_path)
        audit_files = list((workspace / ".dsim_agent" / "audit").glob("*.jsonl"))
        assert audit_files
        assert "mcp__dsim__OpenDsimProject" in audit_files[0].read_text(encoding="utf-8")
    finally:
        rmtree(workspace, ignore_errors=True)
