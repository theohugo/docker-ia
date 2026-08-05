"""Strict validation of the provider's JSON contract."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .exceptions import AIInvalidResponseError

LIST_FIELDS = ("objectives", "deliverables", "risks", "next_steps")


@dataclass(frozen=True, slots=True)
class AnalysisPayload:
    summary: str
    objectives: list[str]
    deliverables: list[str]
    risks: list[str]
    next_steps: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "objectives": self.objectives,
            "deliverables": self.deliverables,
            "risks": self.risks,
            "next_steps": self.next_steps,
        }


def validate_analysis_payload(value: Any) -> AnalysisPayload:
    if not isinstance(value, Mapping):
        raise AIInvalidResponseError("The analysis root must be a JSON object.")

    summary = value.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise AIInvalidResponseError("The summary must be a non-empty string.")

    lists: dict[str, list[str]] = {}
    for field in LIST_FIELDS:
        items = value.get(field)
        if not isinstance(items, list) or not items:
            raise AIInvalidResponseError(f"{field} must be a non-empty list.")
        if not all(isinstance(item, str) and item.strip() for item in items):
            raise AIInvalidResponseError(f"Every {field} item must be a non-empty string.")
        lists[field] = [item.strip() for item in items]

    return AnalysisPayload(
        summary=summary.strip(),
        objectives=lists["objectives"],
        deliverables=lists["deliverables"],
        risks=lists["risks"],
        next_steps=lists["next_steps"],
    )
