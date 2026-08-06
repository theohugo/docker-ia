"""Thin HTTP views for the brief workflow."""

from functools import partial

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .forms import ProjectBriefForm
from .models import AnalysisResult, GenerationEvent, ProjectBrief
from .services.pdf_export import generate_analysis_pdf
from .tasks import enqueue_brief_generation


@login_required
def dashboard(request):
    queryset = ProjectBrief.objects.filter(user=request.user).select_related("analysis")
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "briefs/dashboard.html",
        {
            "briefs": page_obj,
            "brief_count": paginator.count,
            "is_paginated": page_obj.has_other_pages(),
            "page_obj": page_obj,
        },
    )


@login_required
def create(request):
    form = ProjectBriefForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            brief = form.save(commit=False)
            brief.user = request.user
            brief.status = ProjectBrief.Status.QUEUED
            brief.provider = settings.AI_PROVIDER
            brief.model = settings.AI_MODEL
            brief.prompt_version = settings.AI_PROMPT_VERSION
            brief.save()

            GenerationEvent.objects.create(
                brief=brief,
                event_type=GenerationEvent.Type.QUEUED,
                provider=brief.provider,
                model=brief.model,
                message="Brief enregistré et mis en file.",
            )

            transaction.on_commit(
                partial(
                    enqueue_brief_generation,
                    brief.pk,
                )
            )

        return redirect(
            "briefs:detail",
            pk=brief.pk,
        )

    return render(
        request,
        "briefs/create.html",
        {
            "form": form,
        },
    )


@login_required
def detail(request, pk):
    brief = get_object_or_404(
        ProjectBrief.objects.select_related("analysis").prefetch_related("generation_events"),
        pk=pk,
        user=request.user,
    )

    return render(
        request,
        "briefs/detail.html",
        {
            "brief": brief,
        },
    )


@never_cache
@login_required
def status(request, pk):
    brief = get_object_or_404(
        ProjectBrief,
        pk=pk,
        user=request.user,
    )

    has_analysis = hasattr(brief, "analysis")

    payload = {
        "id": str(brief.pk),
        "status": brief.status,
        "is_terminal": brief.is_terminal,
        "has_analysis": has_analysis,
        "updated_at": brief.updated_at.isoformat(),
        "error": (
            {
                "code": brief.error_code,
                "message": brief.error_message,
            }
            if brief.status == ProjectBrief.Status.FAILED
            else None
        ),
        "analysis_url": (
            reverse(
                "briefs:detail",
                kwargs={
                    "pk": brief.pk,
                },
            )
            if brief.status == ProjectBrief.Status.COMPLETED and has_analysis
            else None
        ),
    }

    return JsonResponse(payload)


@require_GET
@login_required
def download_pdf(request, pk):
    """Generate and securely download the PDF owned by the current user."""

    brief = get_object_or_404(
        ProjectBrief.objects.select_related("analysis"),
        pk=pk,
        user=request.user,
    )

    if brief.status != ProjectBrief.Status.COMPLETED:
        raise Http404("Cette analyse n'est pas terminée.")

    try:
        analysis: AnalysisResult = brief.analysis
    except AnalysisResult.DoesNotExist as exc:
        raise Http404("Aucun résultat n'est disponible.") from exc

    pdf_is_missing = not analysis.pdf_file or not analysis.pdf_file.storage.exists(
        analysis.pdf_file.name,
    )
    pdf_is_stale = not analysis.pdf_generated_at or analysis.pdf_generated_at < analysis.updated_at

    if pdf_is_missing or pdf_is_stale:
        generate_analysis_pdf(analysis)
        analysis.refresh_from_db(
            fields=[
                "pdf_file",
                "pdf_generated_at",
            ]
        )

    if not analysis.pdf_file:
        raise Http404("Le fichier PDF n'a pas pu être généré.")

    safe_title = slugify(brief.title)[:60] or "brief"
    download_name = f"cadria-{safe_title}.pdf"

    analysis.pdf_file.open("rb")

    return FileResponse(
        analysis.pdf_file,
        as_attachment=True,
        filename=download_name,
        content_type="application/pdf",
    )
