from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from briefs.models import AnalysisResult, GenerationEvent, ProjectBrief
from briefs.tests.factories import make_brief, make_user


class BriefViewTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_only_contains_owned_briefs(self):
        own = make_brief(self.user, title="Mon brief")
        make_brief(make_user("someone-else"), title="Brief privé")
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["briefs"], [own])

    def test_dashboard_paginates_long_history(self):
        for index in range(13):
            make_brief(self.user, title=f"Brief {index:02d}")
        self.client.force_login(self.user)

        first_page = self.client.get(reverse("dashboard"))
        second_page = self.client.get(reverse("dashboard"), {"page": 2})

        self.assertEqual(len(first_page.context["briefs"]), 12)
        self.assertTrue(first_page.context["is_paginated"])
        self.assertEqual(first_page.context["brief_count"], 13)
        self.assertEqual(len(second_page.context["briefs"]), 1)

    def test_dashboard_searches_owned_briefs_by_title_or_idea(self):
        title_match = make_brief(
            self.user,
            title="Refonte du portail",
            raw_idea="Centraliser les documents des équipes.",
        )
        idea_match = make_brief(self.user, title="Assistant interne", raw_idea="Simplifier le support client")
        make_brief(self.user, title="Projet sans rapport", raw_idea="Organiser les congés")
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"), {"q": "portail"})
        self.assertQuerySetEqual(response.context["briefs"], [title_match])

        response = self.client.get(reverse("dashboard"), {"q": "support"})
        self.assertQuerySetEqual(response.context["briefs"], [idea_match])
        self.assertEqual(response.context["active_query"], "support")

    def test_dashboard_filters_by_status_and_ignores_unknown_status(self):
        completed = make_brief(self.user, title="Brief prêt", status=ProjectBrief.Status.COMPLETED)
        make_brief(self.user, title="Brief en cours", status=ProjectBrief.Status.PROCESSING)
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"), {"status": ProjectBrief.Status.COMPLETED})
        self.assertQuerySetEqual(response.context["briefs"], [completed])
        self.assertEqual(response.context["active_status"], ProjectBrief.Status.COMPLETED)

        response = self.client.get(reverse("dashboard"), {"status": "not-a-status"})
        self.assertEqual(response.context["brief_count"], 2)
        self.assertEqual(response.context["active_status"], "")

    def test_detail_hides_another_users_brief(self):
        brief = make_brief(make_user("someone-else"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("briefs:detail", kwargs={"pk": brief.pk}))

        self.assertEqual(response.status_code, 404)

    @patch("briefs.views.enqueue_brief_generation")
    def test_valid_create_queues_generation_after_commit(self, enqueue):
        self.client.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("briefs:create"),
                {
                    "title": "Assistant de cadrage",
                    "raw_idea": "Transformer chaque idée initiale en un plan clair et priorisé.",
                    "audience": "Chefs de projet",
                    "constraints": "Réponse structurée en moins d'une minute.",
                },
            )

        brief = ProjectBrief.objects.get(user=self.user)
        self.assertRedirects(response, reverse("briefs:detail", kwargs={"pk": brief.pk}))
        self.assertEqual(brief.status, ProjectBrief.Status.QUEUED)
        self.assertEqual(brief.generation_events.get().event_type, GenerationEvent.Type.QUEUED)
        enqueue.assert_called_once_with(brief.pk)

    def test_failed_status_returns_safe_structured_error(self):
        brief = make_brief(
            self.user,
            status=ProjectBrief.Status.FAILED,
            error_code="provider_quota",
            error_message="Le quota est atteint.",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("briefs:status", kwargs={"pk": brief.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["error"],
            {"code": "provider_quota", "message": "Le quota est atteint."},
        )
        self.assertTrue(response.json()["is_terminal"])
        self.assertEqual(response["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    def test_completed_status_exposes_owned_detail_url(self):
        brief = make_brief(self.user, status=ProjectBrief.Status.COMPLETED)
        AnalysisResult.objects.create(
            brief=brief,
            summary="Synthèse",
            objectives=["Objectif"],
            deliverables=["Livrable"],
            risks=["Risque"],
            next_steps=["Étape"],
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("briefs:status", kwargs={"pk": brief.pk}))

        self.assertTrue(response.json()["has_analysis"])
        self.assertEqual(
            response.json()["analysis_url"],
            reverse("briefs:detail", kwargs={"pk": brief.pk}),
        )

    def test_status_hides_another_users_brief(self):
        brief = make_brief(make_user("someone-else"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("briefs:status", kwargs={"pk": brief.pk}))

        self.assertEqual(response.status_code, 404)


class HealthViewTests(TestCase):
    def test_health_checks_database(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
