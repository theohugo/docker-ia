from unittest.mock import patch

from django.test import TestCase

from briefs.models import AnalysisResult, GenerationEvent, ProjectBrief
from briefs.services import AIQuotaError, AnalysisOutput
from briefs.services.schema import AnalysisPayload
from briefs.tasks import enqueue_brief_generation, generate_brief_analysis
from briefs.tests.factories import make_brief, make_user


def analysis_output():
    return AnalysisOutput(
        payload=AnalysisPayload(
            summary="Un brief clarifié.",
            objectives=["Valider le besoin"],
            deliverables=["Prototype"],
            risks=["Délai"],
            next_steps=["Entretien utilisateur"],
        ),
        raw_response={"request_id": "demo-1"},
        tokens_used=147,
        duration_ms=84,
        provider="demo",
        model="demo-cadria-v1",
    )


class GenerationTaskTests(TestCase):
    def setUp(self):
        self.brief = make_brief(make_user())

    @patch("briefs.tasks.analyse_brief", return_value=analysis_output())
    def test_success_persists_structured_result_and_events(self, analyse):
        result = generate_brief_analysis.run(str(self.brief.pk))

        self.brief.refresh_from_db()
        analysis = AnalysisResult.objects.get(brief=self.brief)
        self.assertEqual(result["status"], ProjectBrief.Status.COMPLETED)
        self.assertEqual(self.brief.status, ProjectBrief.Status.COMPLETED)
        self.assertEqual(analysis.objectives, ["Valider le besoin"])
        self.assertEqual(analysis.tokens_used, 147)
        self.assertEqual(analysis.duration_ms, 84)
        self.assertEqual(
            list(self.brief.generation_events.values_list("event_type", flat=True)),
            [GenerationEvent.Type.STARTED, GenerationEvent.Type.COMPLETED],
        )
        analyse.assert_called_once()

    @patch("briefs.tasks.analyse_brief", side_effect=AIQuotaError())
    def test_known_failure_saves_public_error_without_raw_provider_detail(self, analyse):
        result = generate_brief_analysis.run(str(self.brief.pk))

        self.brief.refresh_from_db()
        self.assertEqual(result["error_code"], "provider_quota")
        self.assertEqual(self.brief.status, ProjectBrief.Status.FAILED)
        self.assertEqual(self.brief.error_code, "provider_quota")
        self.assertEqual(self.brief.error_message, AIQuotaError.public_message)
        self.assertFalse(AnalysisResult.objects.filter(brief=self.brief).exists())
        self.assertEqual(self.brief.generation_events.last().event_type, GenerationEvent.Type.FAILED)

    @patch("briefs.tasks.analyse_brief", side_effect=RuntimeError("secret-provider-payload"))
    def test_unexpected_failure_uses_generic_public_error(self, analyse):
        result = generate_brief_analysis.run(str(self.brief.pk))

        self.brief.refresh_from_db()
        self.assertEqual(result["error_code"], "internal_error")
        self.assertNotIn("secret-provider-payload", self.brief.error_message)

    def test_completed_task_is_idempotent(self):
        self.brief.status = ProjectBrief.Status.COMPLETED
        self.brief.save(update_fields=["status", "updated_at"])

        with patch("briefs.tasks.analyse_brief") as analyse:
            result = generate_brief_analysis.run(str(self.brief.pk))

        self.assertEqual(result["status"], ProjectBrief.Status.COMPLETED)
        analyse.assert_not_called()
        self.assertFalse(self.brief.generation_events.exists())

    def test_unknown_brief_is_ignored(self):
        result = generate_brief_analysis.run("00000000-0000-0000-0000-000000000000")

        self.assertEqual(result["status"], "not_found")

    @patch("briefs.tasks.generate_brief_analysis.delay", side_effect=ConnectionError("redis unavailable"))
    def test_broker_failure_marks_brief_as_failed(self, delay):
        enqueue_brief_generation(self.brief.pk)

        self.brief.refresh_from_db()
        self.assertEqual(self.brief.status, ProjectBrief.Status.FAILED)
        self.assertEqual(self.brief.error_code, "queue_unavailable")
