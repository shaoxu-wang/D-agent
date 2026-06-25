"""Helpers for adapting DSim workflow results to agent tool results."""

from __future__ import annotations

from typing import Any

from cc.tools.base import ToolResult


def workflow_tool_result(
    result: Any,
    *,
    success_content: str,
    failure_prefix: str,
) -> ToolResult:
    """Return a ToolResult whose error flag mirrors the workflow payload."""
    structured = result.model_dump() if hasattr(result, "model_dump") else result
    is_error = _workflow_failed(structured)
    content = success_content
    if is_error:
        error = _workflow_error_message(structured)
        content = f"{failure_prefix} failed"
        if error:
            content = f"{content}: {error}"
        content = f"{content}."
    return ToolResult(content=content, is_error=is_error, metadata={"structured": structured})


def _workflow_failed(structured: Any) -> bool:
    if not isinstance(structured, dict):
        return False
    summary = structured.get("summary")
    if isinstance(summary, dict) and summary.get("ok") is False:
        return True
    steps = structured.get("steps")
    if isinstance(steps, list):
        return any(isinstance(step, dict) and step.get("status") == "failed" for step in steps)
    return False


def _workflow_error_message(structured: Any) -> str:
    if not isinstance(structured, dict):
        return ""
    summary = structured.get("summary")
    if isinstance(summary, dict):
        error = summary.get("error")
        if isinstance(error, str):
            return error
        if error is not None:
            return str(error)
    steps = structured.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") == "failed":
                message = step.get("error_message")
                return str(message) if message else ""
    return ""
