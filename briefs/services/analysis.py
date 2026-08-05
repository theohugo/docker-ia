"""Provider-independent brief analysis orchestration."""

from dataclasses import dataclass
from time import monotonic
from typing import Any

from django.conf import settings

from .exceptions import AIInvalidInputError
from .providers import get_provider
from .schema import AnalysisPayload


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    payload: AnalysisPayload
    raw_response: dict[str, Any]
    tokens_used: int
    duration_ms: int
    provider: str
    model: str


def analyse_brief(brief) -> AnalysisOutput:
    """Analyse a persisted brief using its configured provider and model."""
    values = (brief.title, brief.raw_idea, brief.audience, brief.constraints)
    total_chars = sum(len(value) for value in values)
    if total_chars > settings.AI_MAX_INPUT_CHARS:
        raise AIInvalidInputError("The persisted brief exceeds AI_MAX_INPUT_CHARS.")
    if not brief.raw_idea.strip() or not brief.audience.strip():
        raise AIInvalidInputError("The persisted brief is incomplete.")

    provider = get_provider(brief.provider, brief.model)
    started_at = monotonic()
    response = provider.analyse(
        title=brief.title,
        raw_idea=brief.raw_idea,
        audience=brief.audience,
        constraints=brief.constraints,
    )
    duration_ms = max(0, round((monotonic() - started_at) * 1000))
    return AnalysisOutput(
        payload=response.payload,
        raw_response=response.raw_response,
        tokens_used=response.tokens_used,
        duration_ms=duration_ms,
        provider=provider.name,
        model=provider.model,
    )
