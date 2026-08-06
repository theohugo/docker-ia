import tempfile
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from briefs.models import AnalysisResult, ProjectBrief
from briefs.services.pdf_export import generate_analysis_pdf
from briefs.tests.factories import make_brief, make_user


class PdfExportTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)

        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.user = make_user()
        self.brief, self.analysis = self._create_completed_analysis(self.user)

    def _create_completed_analysis(self, user):
        brief = make_brief(
            user,
            title="Projet PDF",
            status=ProjectBrief.Status.COMPLETED,
            provider="ollama",
            model="qwen2.5:0.5b",
        )

        analysis = AnalysisResult.objects.create(
            brief=brief,
            summary="Une synthèse claire du projet.",
            objectives=[
                "Valider le besoin utilisateur.",
                "Construire une première version.",
            ],
            deliverables=[
                "Un prototype fonctionnel.",
                "Une documentation utilisateur.",
            ],
            risks=[
                "Un périmètre trop large.",
                "Un délai de développement insuffisant.",
            ],
            next_steps=[
                "Interroger les futurs utilisateurs.",
                "Prioriser les fonctionnalités.",
            ],
            tokens_used=384,
            duration_ms=39298,
        )

        return brief, analysis

    def test_generate_analysis_pdf_persists_valid_pdf(self):
        stored_name = generate_analysis_pdf(self.analysis)

        self.analysis.refresh_from_db()

        self.assertEqual(stored_name, self.analysis.pdf_file.name)
        self.assertTrue(self.analysis.pdf_file.name.endswith(".pdf"))
        self.assertIsNotNone(self.analysis.pdf_generated_at)
        self.assertTrue(
            self.analysis.pdf_file.storage.exists(
                self.analysis.pdf_file.name,
            )
        )

        with self.analysis.pdf_file.storage.open(
            self.analysis.pdf_file.name,
            "rb",
        ) as pdf_file:
            self.assertEqual(pdf_file.read(4), b"%PDF")

    def test_download_requires_authentication(self):
        url = reverse(
            "briefs:download_pdf",
            kwargs={"pk": self.brief.pk},
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
        )

    def test_owner_can_generate_and_download_pdf(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "briefs:download_pdf",
                kwargs={"pk": self.brief.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn(
            "cadria-projet-pdf.pdf",
            response["Content-Disposition"],
        )

        pdf_content = b"".join(response.streaming_content)

        self.assertTrue(pdf_content.startswith(b"%PDF"))

        self.analysis.refresh_from_db()
        self.assertTrue(self.analysis.pdf_file)
        self.assertIsNotNone(self.analysis.pdf_generated_at)

    def test_another_user_cannot_download_the_pdf(self):
        other_user = make_user("other-user")
        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                "briefs:download_pdf",
                kwargs={"pk": self.brief.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_uncompleted_brief_cannot_be_exported(self):
        queued_brief = make_brief(
            self.user,
            title="Brief encore en attente",
            status=ProjectBrief.Status.QUEUED,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "briefs:download_pdf",
                kwargs={"pk": queued_brief.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    @patch("briefs.views.generate_analysis_pdf")
    def test_existing_pdf_is_reused(self, generate_pdf):
        self.analysis.pdf_file.save(
            "existing-export.pdf",
            ContentFile(b"%PDF-existing-export"),
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "briefs:download_pdf",
                kwargs={"pk": self.brief.pk},
            )
        )

        pdf_content = b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(pdf_content.startswith(b"%PDF"))
        generate_pdf.assert_not_called()
