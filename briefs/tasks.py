"""Celery tasks that run AI work outside the request/response cycle."""

import logging
from uuid import UUID

from celery import shared_task
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AnalysisResult, GenerationEvent, ProjectBrief
from .services import AIServiceError, analyse_brief

logger = logging.getLogger(__name__)


def enqueue_brief_generation(brief_id: UUID | str) -> None:
    """Enqueue a brief without turning broker downtime into a server error."""
    try:
        generate_brief_analysis.delay(str(brief_id))
    except Exception as exc:  # The broker can fail through several transport-specific exceptions.
        logger.error(
            "Could not enqueue brief generation brief_id=%s exception_type=%s",
            brief_id,
            type(exc).__name__,
        )
        _mark_failed(
            brief_id,
            code="queue_unavailable",
            message="Le service d'analyse est momentanément indisponible. Réessayez plus tard.",
        )


@shared_task(bind=True, name="briefs.generate_analysis", max_retries=2)
def generate_brief_analysis(self, brief_id: str) -> dict[str, str]:
    brief = _mark_processing(brief_id)
    if brief is None:
        return {"id": str(brief_id), "status": "not_found"}
    if brief.status == ProjectBrief.Status.COMPLETED:
        return {"id": str(brief.pk), "status": ProjectBrief.Status.COMPLETED}

    try:
        output = analyse_brief(brief)
    except AIServiceError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            _mark_retrying(brief.pk, exc.code, self.request.retries + 1)
            raise self.retry(exc=exc, countdown=5 * (2**self.request.retries)) from exc
        logger.warning(
            "AI generation failed brief_id=%s provider=%s code=%s",
            brief.pk,
            brief.provider,
            exc.code,
        )
        _mark_failed(brief.pk, code=exc.code, message=exc.public_message)
        return {"id": str(brief.pk), "status": ProjectBrief.Status.FAILED, "error_code": exc.code}
    except Exception as exc:
        # Do not interpolate the exception text: third-party errors may contain credentials.
        logger.error(
            "Unexpected AI generation failure brief_id=%s provider=%s exception_type=%s",
            brief.pk,
            brief.provider,
            type(exc).__name__,
        )
        _mark_failed(
            brief.pk,
            code="internal_error",
            message="Une erreur inattendue a interrompu l'analyse.",
        )
        return {
            "id": str(brief.pk),
            "status": ProjectBrief.Status.FAILED,
            "error_code": "internal_error",
        }

    with transaction.atomic():
        locked_brief = ProjectBrief.objects.select_for_update().get(pk=brief.pk)
        payload = output.payload.as_dict()
        AnalysisResult.objects.update_or_create(
            brief=locked_brief,
            defaults={
                **payload,
                "raw_response": output.raw_response,
                "tokens_used": output.tokens_used,
                "duration_ms": output.duration_ms,
            },
        )
        locked_brief.status = ProjectBrief.Status.COMPLETED
        locked_brief.provider = output.provider
        locked_brief.model = output.model
        locked_brief.error_code = ""
        locked_brief.error_message = ""
        locked_brief.save(
            update_fields=[
                "status",
                "provider",
                "model",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        GenerationEvent.objects.create(
            brief=locked_brief,
            event_type=GenerationEvent.Type.COMPLETED,
            provider=output.provider,
            model=output.model,
            message=(
                "Analyse structurée enregistrée via le fournisseur de secours."
                if output.fallback_used
                else "Analyse structurée enregistrée."
            ),
            metadata={
                "tokens_used": output.tokens_used,
                "duration_ms": output.duration_ms,
                "fallback_used": output.fallback_used,
                "primary_provider": output.primary_provider,
                "primary_error_code": output.primary_error_code,
            },
        )

    logger.info(
        "AI generation completed brief_id=%s provider=%s model=%s duration_ms=%s",
        brief.pk,
        output.provider,
        output.model,
        output.duration_ms,
    )
    return {"id": str(brief.pk), "status": ProjectBrief.Status.COMPLETED}


def _mark_processing(brief_id: UUID | str) -> ProjectBrief | None:
    try:
        with transaction.atomic():
            brief = ProjectBrief.objects.select_for_update().get(pk=brief_id)
            if brief.status == ProjectBrief.Status.COMPLETED:
                return brief
            brief.status = ProjectBrief.Status.PROCESSING
            brief.error_code = ""
            brief.error_message = ""
            brief.save(update_fields=["status", "error_code", "error_message", "updated_at"])
            GenerationEvent.objects.create(
                brief=brief,
                event_type=GenerationEvent.Type.STARTED,
                provider=brief.provider,
                model=brief.model,
                message="Analyse démarrée par le worker.",
            )
            return brief
    except (ProjectBrief.DoesNotExist, ValidationError, ValueError):
        logger.warning("Brief generation ignored because the brief does not exist brief_id=%s", brief_id)
        return None


def _mark_retrying(brief_id: UUID | str, error_code: str, attempt: int) -> None:
    with transaction.atomic():
        brief = ProjectBrief.objects.select_for_update().get(pk=brief_id)
        brief.status = ProjectBrief.Status.QUEUED
        brief.error_code = ""
        brief.error_message = ""
        brief.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        GenerationEvent.objects.create(
            brief=brief,
            event_type=GenerationEvent.Type.RETRYING,
            provider=brief.provider,
            model=brief.model,
            message="Nouvelle tentative planifiée.",
            metadata={"attempt": attempt, "error_code": error_code},
        )


def _mark_failed(brief_id: UUID | str, *, code: str, message: str) -> None:
    try:
        with transaction.atomic():
            brief = ProjectBrief.objects.select_for_update().get(pk=brief_id)
            brief.status = ProjectBrief.Status.FAILED
            brief.error_code = code
            brief.error_message = message
            brief.save(update_fields=["status", "error_code", "error_message", "updated_at"])
            GenerationEvent.objects.create(
                brief=brief,
                event_type=GenerationEvent.Type.FAILED,
                provider=brief.provider,
                model=brief.model,
                message=message,
                metadata={"error_code": code},
            )
    except (ProjectBrief.DoesNotExist, ValidationError, ValueError):
        logger.warning("Could not mark missing brief as failed brief_id=%s", brief_id)
