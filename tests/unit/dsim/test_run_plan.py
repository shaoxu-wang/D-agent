from cc.dsim.memory_context import MemoryContext, MemoryContextItem
from cc.dsim.run_plan import RunPlanBuilder


def test_run_plan_suggest_only_keeps_prefill_as_suggestions() -> None:
    memory_context = MemoryContext(
        project_id="project-run",
        applies_to="single_run",
        memories=[
            MemoryContextItem(
                memory_id="m1",
                kind="operating_profile",
                content="Use tolerance 1e-6 and max iterations 200.",
                applies_to=["single_run"],
                evidence_refs=[],
                priority=5,
            ),
            MemoryContextItem(
                memory_id="m2",
                kind="project_caution",
                content="Avoid long sweeps on this project.",
                applies_to=["single_run"],
                evidence_refs=[],
                priority=3,
            ),
        ],
        warnings=[],
    )

    plan = RunPlanBuilder().build(
        mode="single_run",
        memory_context=memory_context,
        apply_mode="suggest_only",
    )

    assert plan.apply_mode == "suggest_only"
    assert plan.config_prefill == {}
    assert plan.parameter_prefill == []
    assert plan.memory_hints_used == ["m1", "m2"]
    assert any("Use tolerance" in item for item in plan.suggestions)
    assert any("Avoid long sweeps" in item for item in plan.warnings)
    assert plan.compact()["config_prefill_keys"] == []
    assert plan.compact()["parameter_prefill_names"] == []
    assert plan.compact()["sweep_suggestion_count"] == 0
    assert plan.compact()["requires_confirmation"] is False
    assert "config_prefill" not in plan.compact()


def test_run_plan_apply_prefill_extracts_operating_profile_defaults() -> None:
    memory_context = MemoryContext(
        project_id="project-run",
        applies_to="single_run",
        memories=[
            MemoryContextItem(
                memory_id="m1",
                kind="operating_profile",
                content="Use tolerance 1e-6 and max iterations 200.",
                applies_to=["single_run"],
                evidence_refs=[],
                priority=5,
            ),
        ],
        warnings=[],
    )

    plan = RunPlanBuilder().build(
        mode="single_run",
        memory_context=memory_context,
        apply_mode="apply_prefill",
    )

    assert plan.apply_mode == "apply_prefill"
    assert plan.config_prefill == {"tolerance": 1e-06, "max_iterations": 200}
    assert plan.parameter_prefill == []
    assert plan.memory_hints_used == ["m1"]
    assert plan.compact()["config_prefill_keys"] == ["max_iterations", "tolerance"]
    assert plan.compact()["requires_confirmation"] is True
