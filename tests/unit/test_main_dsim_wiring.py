from types import SimpleNamespace

import pytest

from cc.main import _connect_mcp_servers, _run_print_mode, _run_repl


@pytest.mark.asyncio
async def test_connect_mcp_servers_builds_runtime_after_mcp_connection(monkeypatch) -> None:
    calls: list[str] = []

    def fake_load_mcp_configs(_cwd: str):
        return [SimpleNamespace(name="dsim", transport="stdio")]

    async def fake_connect_mcp_server(_config, _registry):
        calls.append("connect_mcp")

    def fake_has_capability(_registry):
        calls.append("check_capability")
        return True

    bundle = object()
    build_args: dict[str, object] = {}

    def fake_build_dsim_runtime(**kwargs):
        calls.append("build_runtime")
        build_args.update(kwargs)
        return bundle

    def fake_register_dsim_tools(_registry, *, runtime):
        calls.append("register_tools")
        assert runtime is bundle

    monkeypatch.setattr("cc.mcp.config.load_mcp_configs", fake_load_mcp_configs)
    monkeypatch.setattr("cc.mcp.client.connect_mcp_server", fake_connect_mcp_server)
    monkeypatch.setattr("cc.dsim.registry.has_dsim_mcp_capability", fake_has_capability)
    monkeypatch.setattr("cc.main.build_dsim_runtime", fake_build_dsim_runtime)
    monkeypatch.setattr("cc.dsim.registry.register_dsim_tools", fake_register_dsim_tools)

    registry = object()
    await _connect_mcp_servers(
        "workspace",
        registry,
        permission_ctx=object(),
        session_id="test-session",
    )

    assert calls == ["connect_mcp", "check_capability", "build_runtime", "register_tools"]
    assert build_args["session_id"] == "test-session"
    assert build_args["permission_ctx"] is not None


@pytest.mark.asyncio
async def test_run_print_mode_allocates_session_before_mcp(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class FakeEngine:
        def __init__(self) -> None:
            self.registry = object()
            self.permission_ctx = object()

        async def submit(self, prompt: str, max_turns: int = 20):
            events.append(("submit", prompt))
            if False:
                yield None

    fake_engine = FakeEngine()

    async def fake_connect_mcp_servers(cwd, registry, *, permission_ctx, session_id):
        events.append(("connect", session_id))
        assert permission_ctx is fake_engine.permission_ctx

    monkeypatch.setattr("cc.main._load_env", lambda: {"ANTHROPIC_API_KEY": "key"})
    monkeypatch.setattr("cc.main.create_client", lambda **kwargs: object())
    monkeypatch.setattr("cc.main._build_engine", lambda *args, **kwargs: fake_engine)
    monkeypatch.setattr("cc.main._connect_mcp_servers", fake_connect_mcp_servers)
    monkeypatch.setattr("cc.main.render_event", lambda event: None)

    await _run_print_mode("hello", "test-model")

    assert events[0][0] == "connect"
    assert str(events[0][1]).startswith("print-")
    assert events[1] == ("submit", "hello")


@pytest.mark.asyncio
async def test_run_repl_allocates_session_before_mcp(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class FakeEngine:
        def __init__(self) -> None:
            self.registry = object()
            self.permission_ctx = object()
            self.model = "test-model"
            self.system_prompt = "test"
            self.messages = []
            self.total_input_tokens = 0
            self.total_output_tokens = 0

        async def run_turn(self):
            if False:
                yield None

    fake_engine = FakeEngine()

    async def fake_connect_mcp_servers(cwd, registry, *, permission_ctx, session_id):
        events.append(("connect", session_id))
        assert permission_ctx is fake_engine.permission_ctx

    monkeypatch.setattr("cc.main._load_env", lambda: {"ANTHROPIC_API_KEY": "key"})
    monkeypatch.setattr("cc.main.create_client", lambda **kwargs: object())
    monkeypatch.setattr("cc.main._build_engine", lambda *args, **kwargs: fake_engine)
    monkeypatch.setattr("cc.main._connect_mcp_servers", fake_connect_mcp_servers)
    monkeypatch.setattr("cc.ui.renderer.print_welcome", lambda: None)
    monkeypatch.setattr("cc.main._read_multiline_input", lambda: (_ for _ in ()).throw(EOFError()))
    monkeypatch.setattr("cc.main.add_to_history", lambda *args, **kwargs: None)
    monkeypatch.setattr("cc.main.save_session", lambda *args, **kwargs: None)
    monkeypatch.setattr("cc.main.render_event", lambda event: None)

    await _run_repl("test-model", resume_id=None)

    assert events[0][0] == "connect"
    assert len(str(events[0][1])) > 0
