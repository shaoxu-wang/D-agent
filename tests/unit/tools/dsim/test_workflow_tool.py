import pytest

from cc.tools.dsim.workflow_tool import RunDsimEngineeringWorkflowTool


class FakeWorkflowService:
    def __init__(self) -> None:
        self.calls = []
        self.result = None

    async def run(self, request):
        self.calls.append(request)
        return self.result or {"mode": request.mode.value, "ok": True}


def test_workflow_tool_schema_requires_explicit_mode() -> None:
    schema = RunDsimEngineeringWorkflowTool(workflow_service=object()).get_schema()

    assert schema.name == "RunDsimEngineeringWorkflow"
    assert "mode" in schema.input_schema["required"]
    assert schema.input_schema["properties"]["mode"]["enum"] == [
        "inspect_only",
        "single_run",
        "diagnose_existing",
        "report_existing",
        "sweep",
    ]
    assert "config" in schema.input_schema["properties"]
    assert "combinations" in schema.input_schema["properties"]
    assert "runs" in schema.input_schema["properties"]
    assert "timeout_seconds" in schema.input_schema["properties"]


@pytest.mark.asyncio
async def test_workflow_tool_rejects_missing_mode() -> None:
    tool = RunDsimEngineeringWorkflowTool(workflow_service=object())

    result = await tool.execute({"project_id": "project-1"})

    assert result.is_error is True
    assert "mode" in result.text


@pytest.mark.asyncio
async def test_workflow_tool_delegates_to_workflow_service() -> None:
    service = FakeWorkflowService()
    tool = RunDsimEngineeringWorkflowTool(workflow_service=service)

    result = await tool.execute({"mode": "inspect_only", "project_id": "project-1"})

    assert result.is_error is False
    assert result.metadata["structured"] == {"mode": "inspect_only", "ok": True}
    assert service.calls
    assert service.calls[0].project_id == "project-1"


@pytest.mark.asyncio
async def test_workflow_tool_marks_failed_workflow_result_as_error() -> None:
    service = FakeWorkflowService()
    service.result = {
        "summary": {"ok": False, "error": "handle_id is required"},
        "steps": [{"name": "run_single", "status": "failed"}],
    }
    tool = RunDsimEngineeringWorkflowTool(workflow_service=service)

    result = await tool.execute({"mode": "single_run", "project_id": "project-1"})

    assert result.is_error is True
    assert "failed" in result.text.lower()
    assert "handle_id is required" in result.text


@pytest.mark.asyncio
async def test_workflow_tool_preserves_workflow_payload_fields() -> None:
    service = FakeWorkflowService()
    tool = RunDsimEngineeringWorkflowTool(workflow_service=service)

    await tool.execute(
        {
            "mode": "sweep",
            "project_id": "project-2",
            "config": {"solver": "mock"},
            "parameters": [{"name": "alpha", "value": 1}],
            "combinations": [{"parameter": "alpha", "value": 1}],
            "runs": [{"run_id": "run-1", "status": "completed"}],
            "timeout_seconds": 30,
            "status": "failed",
            "error": {"code": "SOLVER_FAILED"},
        }
    )

    request = service.calls[0]
    assert request.config == {"solver": "mock"}
    assert request.combinations == [{"parameter": "alpha", "value": 1}]
    assert request.runs == [{"run_id": "run-1", "status": "completed"}]
    assert request.timeout_seconds == 30
    assert request.status == "failed"
    assert request.error == {"code": "SOLVER_FAILED"}
