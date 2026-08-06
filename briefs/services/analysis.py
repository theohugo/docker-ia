"""Provider-independent brief analysis orchestration."""

import logging
from dataclasses import dataclass
from time import monotonic
from typing import Any

from django.conf import settings

from .exceptions import AIInvalidInputError, AIServiceError
from .providers import get_provider
from .schema import AnalysisPayload

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    payload: AnalysisPayload
    raw_response: dict[str, Any]
    tokens_used: int
    duration_ms: int
    provider: str
    model: str
    fallback_used: bool = False
    primary_provider: str = ""
    primary_error_code: str = ""


def analyse_brief(brief) -> AnalysisOutput:
    """Analyse a persisted brief using its configured provider and model.

    Falls back to ``AI_FALLBACK_PROVIDER`` when the primary provider raises any
    ``AIServiceError`` and a distinct fallback is configured, so a struggling primary
    (e.g. a local Ollama instance) does not fail the whole request. If the fallback is
    unset, identical to the primary, or fails too, the primary's error is raised as
    before.
    """
    values = (brief.title, brief.raw_idea, brief.audience, brief.constraints)
    total_chars = sum(len(value) for value in values)
    if total_chars > settings.AI_MAX_INPUT_CHARS:
        raise AIInvalidInputError("The persisted brief exceeds AI_MAX_INPUT_CHARS.")
    if not brief.raw_idea.strip() or not brief.audience.strip():
        raise AIInvalidInputError("The persisted brief is incomplete.")

    primary = get_provider(brief.provider, brief.model)
    call_kwargs = {
        "title": brief.title,
        "raw_idea": brief.raw_idea,
        "audience": brief.audience,
        "constraints": brief.constraints,
    }

    started_at = monotonic()
    active_provider = primary
    fallback_used = False
    primary_error_code = ""
    try:
        response = primary.analyse(**call_kwargs)
    except AIServiceError as primary_exc:
        fallback_name = settings.AI_FALLBACK_PROVIDER.strip().lower()
        if not fallback_name or fallback_name == primary.name.strip().lower():
            raise
        try:
            fallback = get_provider(fallback_name)
            response = fallback.analyse(**call_kwargs)
        except AIServiceError as fallback_exc:
            logger.warning(
                "AI fallback unavailable primary=%s primary_code=%s fallback=%s fallback_code=%s",
                primary.name,
                primary_exc.code,
                fallback_name,
                fallback_exc.code,
            )
            raise primary_exc from fallback_exc
        logger.warning(
            "AI fallback used primary=%s primary_code=%s fallback=%s",
            primary.name,
            primary_exc.code,
            fallback_name,
        )
        active_provider = fallback
        fallback_used = True
        primary_error_code = primary_exc.code

    duration_ms = max(0, round((monotonic() - started_at) * 1000))
    return AnalysisOutput(
        payload=response.payload,
        raw_response=response.raw_response,
        tokens_used=response.tokens_used,
        duration_ms=duration_ms,
        provider=active_provider.name,
        model=active_provider.model,
        fallback_used=fallback_used,
        primary_provider=primary.name if fallback_used else "",
        primary_error_code=primary_error_code,
    )
