import pytest

from cc.dsim.permissions import DsimRiskClassifier
from cc.permissions.gate import (
    PermissionContext,
    PermissionDecision,
    PermissionDecisionRecord,
    PermissionMode,
)
from cc.permissions.rules import PermissionRules, apply_rules


def test_dsim_risk_classifier_strong_asks_delete_tools():
    classifier = DsimRiskClassifier()

    assert classifier.classify("mcp__dsim__DeleteCurveData", {"handle_id": "h1"}) == "strong_ask"
    assert classifier.classify("mcp__dsim__SaveSchematicFile", {"path": "case.dsim"}) == "strong_ask"


def test_dsim_risk_classifier_detects_raw_curve_read():
    classifier = DsimRiskClassifier()

    assert classifier.classify("mcp__dsim__GetAllCurveData", {"handle_id": "h1"}) == "ask"
    assert classifier.classify("ReadDsimCurves", {"mode": "raw"}) == "ask"
    assert classifier.classify("ReadDsimCurves", {"mode": "summary"}) == "allow"


def test_dsim_risk_classifier_uses_real_agent_tool_names():
    classifier = DsimRiskClassifier()

    assert classifier.is_dsim_tool("RunDsimEngineeringWorkflow") is True
    assert classifier.is_dsim_tool("RunParameterSweep") is True
    assert classifier.is_dsim_tool("DsimWorkflow") is False
    assert classifier.classify("RunDsimEngineeringWorkflow", {"mode": "single_run"}) == "ask"
    assert classifier.classify("RunParameterSweep", {"combinations": [{"value": 1}]}) == "ask"
    assert classifier.classify("SaveProjectContext", {"kind": "note"}) == "allow"


def test_dsim_risk_classifier_asks_for_large_sweep():
    classifier = DsimRiskClassifier()
    combinations = [{"value": index} for index in range(21)]

    assert classifier.classify("RunParameterSweep", {"combinations": combinations}) == "ask"


def test_permission_decision_record_contains_tool_call_identity():
    record = PermissionDecisionRecord(
        tool_call_id="toolu_1",
        tool_name="mcp__dsim__RunDsimSimulation",
        decision="ask",
        source="dsim_risk",
        allowed=True,
        input_hash="abc123",
        input_summary="handle_id=h1",
    )

    assert record.tool_call_id == "toolu_1"
    assert record.tool_name == "mcp__dsim__RunDsimSimulation"
    assert record.input_hash == "abc123"


def test_permission_rules_support_tool_name_glob():
    rules = PermissionRules(allow=["mcp__dsim__Get*"])

    assert apply_rules(rules, "mcp__dsim__GetDsimProjectSnapshot", {}) == PermissionDecision.ALLOW


async def always_allow_prompt(_tool_name, _tool_input):
    return "a"


async def yes_prompt(_tool_name, _tool_input):
    return "y"


@pytest.mark.asyncio
async def test_strong_ask_cannot_be_saved_as_always_allow():
    ctx = PermissionContext(mode=PermissionMode.DEFAULT, prompt_callback=always_allow_prompt)

    first = await ctx.check_with_record(
        "mcp__dsim__DeleteCurveData",
        {"handle_id": "h1"},
        tool_call_id="toolu_1",
    )
    second = await ctx.check_with_record(
        "mcp__dsim__DeleteCurveData",
        {"handle_id": "h1"},
        tool_call_id="toolu_2",
    )

    assert first.allowed is True
    assert first.decision == "strong_ask"
    assert first.always_allowed is False
    assert second.prompt_shown is True


@pytest.mark.asyncio
async def test_dsim_safe_reads_are_allowed_without_prompt():
    ctx = PermissionContext(mode=PermissionMode.DEFAULT, prompt_callback=yes_prompt)

    record = await ctx.check_with_record(
        "mcp__dsim__GetDsimProjectSnapshot",
        {"project_id": "project-1"},
        tool_call_id="toolu_3",
    )

    assert record.allowed is True
    assert record.source == "dsim_risk"
    assert record.prompt_shown is False


@pytest.mark.asyncio
async def test_check_keeps_boolean_compatibility():
    ctx = PermissionContext(mode=PermissionMode.DEFAULT, prompt_callback=yes_prompt)

    allowed = await ctx.check("mcp__dsim__RunDsimSimulation", {"handle_id": "h1"})

    assert allowed is True
