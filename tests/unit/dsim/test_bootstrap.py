from cc.dsim.bootstrap import bootstrap_dsim_runtime
from cc.tools.base import Tool, ToolRegistry, ToolResult, ToolSchema


class FakeDsimMcpTool(Tool):
    def get_name(self) -> str:
        return "mcp__dsim__OpenDsimProject"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(name=self.get_name(), description="", input_schema={"type": "object"})

    async def execute(self, tool_input: dict) -> ToolResult:
        return ToolResult(content="ok")


def test_bootstrap_dsim_runtime_returns_none_without_mcp_capability(monkeypatch) -> None:
    called = False

    def fake_build_dsim_runtime(**kwargs):
        nonlocal called
        called = True
        return object()

    monkeypatch.setattr("cc.dsim.bootstrap.build_dsim_runtime", fake_build_dsim_runtime)

    runtime = bootstrap_dsim_runtime(
        cwd="workspace",
        registry=ToolRegistry(),
        permission_ctx=object(),
        session_id="session-1",
    )

    assert runtime is None
    assert called is False


def test_bootstrap_dsim_runtime_builds_and_registers_when_mcp_exists(monkeypatch) -> None:
    registry = ToolRegistry()
    registry.register(FakeDsimMcpTool())
    built_runtime = object()
    build_args: dict[str, object] = {}
    registered: dict[str, object] = {}

    def fake_build_dsim_runtime(**kwargs):
        build_args.update(kwargs)
        return built_runtime

    def fake_register_dsim_tools(registry_arg, *, runtime):
        registered["registry"] = registry_arg
        registered["runtime"] = runtime

    monkeypatch.setattr("cc.dsim.bootstrap.build_dsim_runtime", fake_build_dsim_runtime)
    monkeypatch.setattr("cc.dsim.bootstrap.register_dsim_tools", fake_register_dsim_tools)

    runtime = bootstrap_dsim_runtime(
        cwd="workspace",
        registry=registry,
        permission_ctx="permission",
        session_id="session-1",
        client_id="client-1",
    )

    assert runtime is built_runtime
    assert build_args == {
        "workspace": "workspace",
        "session_id": "session-1",
        "permission_ctx": "permission",
        "registry": registry,
        "client_id": "client-1",
    }
    assert registered == {"registry": registry, "runtime": built_runtime}
