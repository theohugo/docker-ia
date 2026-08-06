"""Persistence for briefs, structured analyses, and generation history."""

import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


class ProjectBrief(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        QUEUED = "queued", "En attente"
        PROCESSING = "processing", "Analyse en cours"
        COMPLETED = "completed", "Terminé"
        FAILED = "failed", "Échec"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_briefs",
    )
    title = models.CharField("titre du projet", max_length=180)
    raw_idea = models.TextField("idée initiale")
    audience = models.TextField("public cible")
    constraints = models.TextField("contraintes", blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    provider = models.CharField(max_length=40, default="demo")
    model = models.CharField(max_length=120, default="demo-cadria-v1")
    prompt_version = models.CharField(max_length=32, default="v1")
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "status", "-created_at"],
                name="brief_user_status_idx",
            )
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            self.Status.COMPLETED,
            self.Status.FAILED,
        }


class AnalysisResult(models.Model):
    brief = models.OneToOneField(
        ProjectBrief,
        on_delete=models.CASCADE,
        related_name="analysis",
    )
    summary = models.TextField()
    objectives = models.JSONField(default=list)
    deliverables = models.JSONField(default=list)
    risks = models.JSONField(default=list)
    next_steps = models.JSONField(default=list)
    raw_response = models.JSONField(default=dict)
    tokens_used = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)

    pdf_file = models.FileField(
        upload_to="brief_exports/%Y/%m/",
        blank=True,
    )
    pdf_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "résultat d'analyse"
        verbose_name_plural = "résultats d'analyse"

    def __str__(self) -> str:
        return f"Analyse — {self.brief.title}"


class GenerationEvent(models.Model):
    class Type(models.TextChoices):
        QUEUED = "queued", "Mise en file"
        STARTED = "started", "Démarrée"
        RETRYING = "retrying", "Nouvelle tentative"
        COMPLETED = "completed", "Terminée"
        FAILED = "failed", "Échec"

    brief = models.ForeignKey(
        ProjectBrief,
        on_delete=models.CASCADE,
        related_name="generation_events",
    )
    event_type = models.CharField(
        max_length=16,
        choices=Type.choices,
    )
    provider = models.CharField(max_length=40, blank=True)
    model = models.CharField(max_length=120, blank=True)
    message = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        indexes = [
            models.Index(
                fields=["brief", "created_at"],
                name="event_brief_date_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} — {self.brief.title}"


@receiver(post_delete, sender=AnalysisResult)
def delete_analysis_pdf_file(*, instance, using, **_kwargs):
    """Delete the stored PDF after its analysis is deleted."""

    if not instance.pdf_file:
        return

    storage = instance.pdf_file.storage
    filename = instance.pdf_file.name

    def delete_file():
        storage.delete(filename)

    transaction.on_commit(delete_file, using=using)
