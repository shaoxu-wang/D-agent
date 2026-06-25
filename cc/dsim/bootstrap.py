"""DSim-specific runtime bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cc.dsim.registry import has_dsim_mcp_capability, register_dsim_tools
from cc.dsim.runtime import DsimRuntimeBundle, build_dsim_runtime

if TYPE_CHECKING:
    from cc.tools.base import ToolRegistry


def bootstrap_dsim_runtime(
    *,
    cwd: str,
    registry: ToolRegistry,
    permission_ctx: Any | None,
    session_id: str,
    client_id: str = "local",
) -> DsimRuntimeBundle | None:
    """Build and register the DSim runtime when MCP DSim tools are available."""
    if not has_dsim_mcp_capability(registry):
        return None

    runtime = build_dsim_runtime(
        workspace=cwd,
        session_id=session_id,
        permission_ctx=permission_ctx,
        registry=registry,
        client_id=client_id,
    )
    register_dsim_tools(registry, runtime=runtime)
    return runtime
