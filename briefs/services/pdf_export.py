"""Generate and persist secure PDF exports for CadrIA analyses."""

from collections.abc import Iterable
from html import escape
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from briefs.models import AnalysisResult, ProjectBrief

PRIMARY_COLOR = colors.HexColor("#8B6FF7")
TEXT_COLOR = colors.HexColor("#17131F")
MUTED_COLOR = colors.HexColor("#625C6B")
BORDER_COLOR = colors.HexColor("#DDD7E8")


def generate_analysis_pdf(analysis: AnalysisResult) -> str:
    """Generate a PDF for a completed analysis and save it with Django storage."""

    if analysis.pk is None:
        raise ValueError("The analysis must be saved before generating its PDF.")

    brief = analysis.brief

    if brief.status != ProjectBrief.Status.COMPLETED:
        raise ValueError("A PDF can only be generated for a completed brief.")

    generated_at = timezone.now()
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=24 * mm,
        title=f"CadrIA - {brief.title}",
        author="CadrIA",
        subject="Analyse de brief générée par intelligence artificielle",
    )

    styles = _build_styles()
    story = _build_story(
        analysis=analysis,
        generated_at=generated_at,
        styles=styles,
    )

    def draw_page(canvas, document_template):
        _draw_page_footer(
            canvas=canvas,
            page_number=document_template.page,
            title=brief.title,
        )

    document.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    pdf_content = buffer.getvalue()
    buffer.close()

    filename = _build_filename(brief)

    if analysis.pdf_file:
        analysis.pdf_file.delete(save=False)

    analysis.pdf_file.save(
        filename,
        ContentFile(pdf_content),
        save=False,
    )
    analysis.pdf_generated_at = generated_at
    analysis.save(
        update_fields=[
            "pdf_file",
            "pdf_generated_at",
            "updated_at",
        ]
    )

    return analysis.pdf_file.name


def _build_story(
    *,
    analysis: AnalysisResult,
    generated_at,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    brief = analysis.brief
    created_at = timezone.localtime(brief.created_at)
    local_generated_at = timezone.localtime(generated_at)

    story: list[Flowable] = [
        Paragraph("CADRIA", styles["brand"]),
        Paragraph(_safe_markup(brief.title), styles["title"]),
        Paragraph(
            (
                f"Brief créé le {created_at:%d/%m/%Y à %H:%M}<br/>"
                f"PDF généré le {local_generated_at:%d/%m/%Y à %H:%M}"
            ),
            styles["metadata"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("Contexte transmis", styles["section"]),
        Paragraph("Idée initiale", styles["label"]),
        Paragraph(_safe_markup(brief.raw_idea), styles["body"]),
        Spacer(1, 4 * mm),
        Paragraph("Public cible", styles["label"]),
        Paragraph(_safe_markup(brief.audience), styles["body"]),
        Spacer(1, 4 * mm),
        Paragraph("Contraintes", styles["label"]),
        Paragraph(
            _safe_markup(brief.constraints or "Aucune contrainte précisée."),
            styles["body"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("Analyse générée", styles["section"]),
        Paragraph("Synthèse", styles["label"]),
        Paragraph(_safe_markup(analysis.summary), styles["body"]),
        Spacer(1, 5 * mm),
        Paragraph("Objectifs", styles["label"]),
        _build_list(analysis.objectives, styles["list"]),
        Spacer(1, 5 * mm),
        Paragraph("Livrables", styles["label"]),
        _build_list(analysis.deliverables, styles["list"]),
        Spacer(1, 5 * mm),
        Paragraph("Risques", styles["label"]),
        _build_list(analysis.risks, styles["list"]),
        Spacer(1, 5 * mm),
        Paragraph("Prochaines étapes", styles["label"]),
        _build_list(analysis.next_steps, styles["list"]),
        Spacer(1, 10 * mm),
        Paragraph("Informations techniques", styles["section"]),
        Paragraph(
            (
                f"<b>Fournisseur :</b> {_safe_markup(brief.provider)}<br/>"
                f"<b>Modèle :</b> {_safe_markup(brief.model)}<br/>"
                f"<b>Version du prompt :</b> {_safe_markup(brief.prompt_version)}<br/>"
                f"<b>Durée :</b> {analysis.duration_ms} ms<br/>"
                f"<b>Tokens annoncés :</b> {analysis.tokens_used}"
            ),
            styles["body"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            (
                "Ce document a été généré automatiquement par CadrIA à partir "
                "des informations transmises par l’utilisateur."
            ),
            styles["notice"],
        ),
    ]

    return story


def _build_styles() -> dict[str, ParagraphStyle]:
    base_styles = getSampleStyleSheet()

    return {
        "brand": ParagraphStyle(
            "CadriaBrand",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=PRIMARY_COLOR,
            spaceAfter=3 * mm,
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "CadriaTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            textColor=TEXT_COLOR,
            spaceAfter=4 * mm,
            alignment=TA_CENTER,
        ),
        "metadata": ParagraphStyle(
            "CadriaMetadata",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=MUTED_COLOR,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "CadriaSection",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=PRIMARY_COLOR,
            spaceBefore=3 * mm,
            spaceAfter=5 * mm,
        ),
        "label": ParagraphStyle(
            "CadriaLabel",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=TEXT_COLOR,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "CadriaBody",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=TEXT_COLOR,
        ),
        "list": ParagraphStyle(
            "CadriaList",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=TEXT_COLOR,
        ),
        "notice": ParagraphStyle(
            "CadriaNotice",
            parent=base_styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=12,
            textColor=MUTED_COLOR,
            borderColor=BORDER_COLOR,
            borderWidth=0.5,
            borderPadding=4 * mm,
        ),
    }


def _build_list(
    values: Iterable[object],
    style: ParagraphStyle,
) -> Flowable:
    items = [
        ListItem(
            Paragraph(_safe_markup(value), style),
            leftIndent=2 * mm,
        )
        for value in values
        if str(value).strip()
    ]

    if not items:
        return Paragraph("Aucun élément renseigné.", style)

    return ListFlowable(
        items,
        bulletType="bullet",
        leftIndent=6 * mm,
        bulletFontName="Helvetica",
        bulletFontSize=7,
        bulletColor=PRIMARY_COLOR,
        spaceAfter=2 * mm,
    )


def _safe_markup(value: object) -> str:
    """Escape user-controlled text before passing it to ReportLab Paragraph."""

    text = str(value or "").replace("\x00", "")
    return escape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _build_filename(brief: ProjectBrief) -> str:
    safe_title = slugify(brief.title)[:60] or "brief"
    return f"cadria-{safe_title}-{brief.pk}.pdf"


def _draw_page_footer(
    *,
    canvas,
    page_number: int,
    title: str,
) -> None:
    canvas.saveState()
    canvas.setTitle(f"CadrIA - {title}")
    canvas.setAuthor("CadrIA")
    canvas.setSubject("Analyse de brief générée par intelligence artificielle")

    canvas.setStrokeColor(BORDER_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(
        20 * mm,
        16 * mm,
        A4[0] - 20 * mm,
        16 * mm,
    )

    canvas.setFillColor(MUTED_COLOR)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        20 * mm,
        10 * mm,
        "CadrIA - export sécurisé",
    )
    canvas.drawRightString(
        A4[0] - 20 * mm,
        10 * mm,
        f"Page {page_number}",
    )
    canvas.restoreState()
