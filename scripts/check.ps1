$ErrorActionPreference = 'Stop'

python -m ruff check cc tests
python -m mypy cc
python -m pytest `
  tests/unit/mcp/dsim `
  tests/unit/dsim `
  tests/unit/tools/dsim `
  tests/unit/mcp/test_client_structured.py `
  tests/unit/permissions/test_dsim_permissions.py `
  tests/unit/tools/agent/test_dsim_tool_exclusion.py `
  tests/unit/test_main_dsim_wiring.py `
  tests/unit/core/test_query_engine.py `
  tests/unit/tools/test_mcp_config.py `
  tests/unit/tools/test_tool_search.py `
  tests/unit/tools/test_streaming_executor.py `
  tests/unit/tools/test_base.py `
  tests/unit/permissions/test_gate.py `
  tests/unit/permissions/test_rules.py `
  tests/unit/tools/test_agent_tool.py `
  -k "not TestLoadPermissionRules" `
  -v
