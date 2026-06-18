from dsim_ai_mcp.services.dsim.public_tools import PUBLIC_TOOL_NAMES, register_public_tools


class FakeMcp:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def tool(self, fn):
        self.registered.append(fn.__name__)
        return fn


def test_public_tool_names_do_not_include_raw_curve_or_delete_tools() -> None:
    assert "GetAllCurveData" not in PUBLIC_TOOL_NAMES
    assert "GetCurveData" not in PUBLIC_TOOL_NAMES
    assert "GetCurveFileData" not in PUBLIC_TOOL_NAMES
    assert "DeleteCurveData" not in PUBLIC_TOOL_NAMES
    assert "DeleteAllCurveData" not in PUBLIC_TOOL_NAMES
    assert "SaveSchematicFile" not in PUBLIC_TOOL_NAMES


def test_register_public_tools_registers_allowlisted_workflows() -> None:
    mcp = FakeMcp()

    register_public_tools(mcp)

    assert set(mcp.registered) == set(PUBLIC_TOOL_NAMES)
