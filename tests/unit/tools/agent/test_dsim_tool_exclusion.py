from cc.tools.agent.agent_tool import should_exclude_from_subagent


def test_subagent_excludes_raw_dsim_mcp_tools() -> None:
    assert should_exclude_from_subagent("mcp__dsim__OpenDsimProject") is True


def test_subagent_excludes_agent_side_dsim_tools() -> None:
    assert should_exclude_from_subagent("RunParameterSweep") is True


def test_subagent_keeps_non_dsim_tools() -> None:
    assert should_exclude_from_subagent("FileRead") is False
