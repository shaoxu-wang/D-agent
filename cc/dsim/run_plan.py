"""Lightweight DSim run plan derived from runtime memory context."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from cc.dsim.memory_context import MemoryContext

RunPlanApplyMode = Literal["suggest_only", "apply_prefill"]


@dataclass(frozen=True, slots=True)
class RunPlan:
    mode: str
    apply_mode: RunPlanApplyMode
    config_prefill: dict[str, Any] = field(default_factory=dict)
    parameter_prefill: list[dict[str, Any]] = field(default_factory=list)
    sweep_range_suggestions: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    memory_hints_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def compact(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "apply_mode": self.apply_mode,
            "config_prefill_keys": sorted(self.config_prefill),
            "parameter_prefill_names": [
                str(parameter.get("name")) for parameter in self.parameter_prefill if parameter.get("name") is not None
            ],
            "sweep_suggestion_count": len(self.sweep_range_suggestions),
            "memory_hints_used": self.memory_hints_used,
            "warnings": self.warnings,
            "requires_confirmation": self.apply_mode == "apply_prefill"
            and bool(self.config_prefill or self.parameter_prefill or self.sweep_range_suggestions),
        }


class RunPlanBuilder:
    """Build a lightweight run plan without executing any tools."""

    def build(
        self,
        *,
        mode: str,
        memory_context: MemoryContext,
        apply_mode: RunPlanApplyMode,
    ) -> RunPlan:
        suggestions: list[str] = []
        warnings: list[str] = list(memory_context.warnings)
        config_prefill: dict[str, Any] = {}
        memory_hints_used: list[str] = []

        for memory in memory_context.memories:
            memory_hints_used.append(memory.memory_id)
            if memory.kind in {"project_caution", "diagnostic_hint"}:
                warnings.append(memory.content)
            else:
                suggestions.append(memory.content)
                if apply_mode == "apply_prefill" and memory.kind in {"operating_profile", "project_fact"}:
                    config_prefill.update(_extract_config_defaults(memory.content))

        return RunPlan(
            mode=mode,
            apply_mode=apply_mode,
            config_prefill=config_prefill,
            parameter_prefill=[],
            sweep_range_suggestions=[],
            suggestions=suggestions,
            memory_hints_used=memory_hints_used,
            warnings=warnings,
        )


def _extract_config_defaults(content: str) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    tolerance = re.search(r"tolerance\s+([0-9]+(?:\.[0-9]+)?(?:e[-+]?[0-9]+)?)", content, re.IGNORECASE)
    if tolerance:
        defaults["tolerance"] = float(tolerance.group(1))
    iterations = re.search(r"max(?:imum)? iterations?\s+([0-9]+)", content, re.IGNORECASE)
    if iterations:
        defaults["max_iterations"] = int(iterations.group(1))
    return defaults
