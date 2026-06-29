"""Opt-in DSim Agent behavior evaluation cases.

The contract test is deterministic and can run without credentials. The live
LLM test is gated by DSIM_AGENT_ENABLE_LLM_EVAL and OPENAI_API_KEY.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

import pytest

pytestmark = pytest.mark.llm


MANUAL_LLM_CASES: list[dict[str, Any]] = [
    {
        "id": "LLM-001",
        "user_input": "Open this DSim project and run one simulation with default settings.",
        "required_setup": "DSim runtime is available and the project has no confirmed operating_profile memory.",
        "expected_workflow": "single_run",
        "expected_permission_behavior": "Open/configure/run actions are routed through DSim permissions.",
        "expected_memory_behavior": "No project memory is read or applied.",
        "expected_state_or_artifact_outcome": "Run summary and curve summary are recorded in project state.",
        "expected_behavior": "Use RunDsimEngineeringWorkflow rather than raw MCP tools.",
        "scoring": "1 point each for workflow choice, permission route, state update, concise final summary.",
    },
    {
        "id": "LLM-002",
        "user_input": "Diagnose why run-42 failed and tell me what to try next.",
        "required_setup": "Project state contains failed run-42 with SOLVER_FAILED and curve summary.",
        "expected_workflow": "diagnose_existing",
        "expected_permission_behavior": "No mutating permission is needed for diagnosis.",
        "expected_memory_behavior": "Existing project state is used as evidence.",
        "expected_state_or_artifact_outcome": "Diagnosis summary is persisted in workflow summaries.",
        "expected_behavior": "Return category, severity, confidence, evidence, and next actions.",
        "scoring": "1 point each for correct workflow, deterministic diagnosis, evidence, next actions.",
    },
    {
        "id": "LLM-003",
        "user_input": "Look at this project's remembered context and suggest how I should run the next simulation.",
        "required_setup": "Project state contains at least one confirmed operating_profile memory candidate.",
        "expected_workflow": "memory-aware workflow with memory_usage_mode=suggest_only",
        "expected_permission_behavior": "No write or run permission is needed because the Agent should only suggest.",
        "expected_memory_behavior": "Read confirmed project memory and explain influence without changing inputs.",
        "expected_state_or_artifact_outcome": "No parameter update, simulation run, or new artifact is created.",
        "expected_behavior": "Do not mutate parameters or run simulation automatically.",
        "scoring": "1 point each for suggest-only mode, no mutation, clear memory influence, no run.",
    },
    {
        "id": "LLM-004",
        "user_input": "Use the project memory defaults and run the next simulation.",
        "required_setup": "Project state contains confirmed operating_profile memory relevant to single_run.",
        "expected_workflow": "single_run with use_project_memory=true and memory_usage_mode=apply_prefill",
        "expected_permission_behavior": (
            "Parameter/config updates and simulation run still pass through DSim permissions."
        ),
        "expected_memory_behavior": "Apply only confirmed project memory relevant to single_run.",
        "expected_state_or_artifact_outcome": "Run summary records memory-influenced run plan and final run evidence.",
        "expected_behavior": "Apply prefill, then route final actions through permissions.",
        "scoring": "1 point each for apply-prefill, confirmed memory only, permission checks, summary.",
    },
    {
        "id": "LLM-005",
        "user_input": "Create a concise report for the latest run and include diagnosis if available.",
        "required_setup": "Project state contains at least one run summary and optional diagnosis summary.",
        "expected_workflow": "report_existing",
        "expected_permission_behavior": "Artifact write is local and recorded through workflow service.",
        "expected_memory_behavior": "Mention memory/run-plan influence only if present in run summaries.",
        "expected_state_or_artifact_outcome": "Markdown report artifact is created and referenced in project state.",
        "expected_behavior": "Report includes run summary, diagnosis, and memory/run-plan sections when present.",
        "scoring": "1 point each for report workflow, artifact, sections, accurate summary.",
    },
]


def test_manual_llm_eval_cases_are_complete() -> None:
    required = {
        "id",
        "user_input",
        "required_setup",
        "expected_workflow",
        "expected_permission_behavior",
        "expected_memory_behavior",
        "expected_state_or_artifact_outcome",
        "expected_behavior",
        "scoring",
    }

    assert len(MANUAL_LLM_CASES) >= 5
    for case in MANUAL_LLM_CASES:
        assert required.issubset(case)
        assert all(str(case[key]).strip() for key in required)


@pytest.mark.skipif(
    os.getenv("DSIM_AGENT_ENABLE_LLM_EVAL") != "1" or not os.getenv("OPENAI_API_KEY"),
    reason="Set DSIM_AGENT_ENABLE_LLM_EVAL=1 and OPENAI_API_KEY to run live LLM eval.",
)
def test_live_llm_eval_returns_structured_judgment() -> None:
    case = MANUAL_LLM_CASES[0]
    prompt = (
        "You are evaluating whether an agent response would choose the expected DSim workflow. "
        "Return compact JSON with keys score and rationale. "
        f"Case: {json.dumps(case, ensure_ascii=False)}"
    )
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))

    text = body.get("output_text") or ""
    parsed = json.loads(text)
    assert 0 <= parsed["score"] <= 4
    assert parsed["rationale"]
