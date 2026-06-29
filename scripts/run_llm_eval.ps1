$ErrorActionPreference = 'Stop'

python -m pytest tests/llm/test_dsim_agent_behavior.py::test_manual_llm_eval_cases_are_complete -v

if ($env:DSIM_AGENT_ENABLE_LLM_EVAL -eq '1') {
    python -m pytest tests/llm/test_dsim_agent_behavior.py -m llm -v
} else {
    Write-Host 'Live LLM eval skipped. Set DSIM_AGENT_ENABLE_LLM_EVAL=1 and OPENAI_API_KEY to enable it.'
}
