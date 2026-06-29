from cc.dsim.workflow_utils import render_report_markdown


def test_render_report_markdown_includes_run_diagnosis_and_memory_sections() -> None:
    markdown = render_report_markdown(
        project_id="project-report",
        runs=[
            {
                "run_id": "run-1",
                "status": "failed",
                "diagnosis": {
                    "category": "solver_convergence",
                    "severity": "high",
                    "confidence": 0.85,
                    "next_actions": ["Review solver tolerance."],
                },
                "run_plan": {
                    "apply_mode": "apply_prefill",
                    "memory_hints_used": ["m-profile"],
                    "warnings": ["Avoid long sweeps."],
                },
            }
        ],
    )

    assert "# DSim Report: project-report" in markdown
    assert "## Run Summary" in markdown
    assert "- run-1: failed" in markdown
    assert "## Diagnosis" in markdown
    assert "solver_convergence" in markdown
    assert "Review solver tolerance." in markdown
    assert "## Memory And Run Plan" in markdown
    assert "apply_prefill" in markdown
    assert "m-profile" in markdown
