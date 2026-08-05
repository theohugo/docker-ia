# Generated for the initial CadrIA schema.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectBrief",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("title", models.CharField(max_length=180, verbose_name="titre du projet")),
                ("raw_idea", models.TextField(verbose_name="idée initiale")),
                ("audience", models.TextField(verbose_name="public cible")),
                ("constraints", models.TextField(blank=True, verbose_name="contraintes")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Brouillon"),
                            ("queued", "En attente"),
                            ("processing", "Analyse en cours"),
                            ("completed", "Terminé"),
                            ("failed", "Échec"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("provider", models.CharField(default="demo", max_length=40)),
                ("model", models.CharField(default="demo-cadria-v1", max_length=120)),
                ("prompt_version", models.CharField(default="v1", max_length=32)),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_briefs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "status", "-created_at"],
                        name="brief_user_status_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="AnalysisResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("summary", models.TextField()),
                ("objectives", models.JSONField(default=list)),
                ("deliverables", models.JSONField(default=list)),
                ("risks", models.JSONField(default=list)),
                ("next_steps", models.JSONField(default=list)),
                ("raw_response", models.JSONField(default=dict)),
                ("tokens_used", models.PositiveIntegerField(default=0)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "brief",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis",
                        to="briefs.projectbrief",
                    ),
                ),
            ],
            options={
                "verbose_name": "résultat d'analyse",
                "verbose_name_plural": "résultats d'analyse",
            },
        ),
        migrations.CreateModel(
            name="GenerationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("queued", "Mise en file"),
                            ("started", "Démarrée"),
                            ("retrying", "Nouvelle tentative"),
                            ("completed", "Terminée"),
                            ("failed", "Échec"),
                        ],
                        max_length=16,
                    ),
                ),
                ("provider", models.CharField(blank=True, max_length=40)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("message", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "brief",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generation_events",
                        to="briefs.projectbrief",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "pk"],
                "indexes": [
                    models.Index(fields=["brief", "created_at"], name="event_brief_date_idx")
                ],
            },
        ),
    ]
