from django.db import IntegrityError, transaction
from django.test import TestCase

from briefs.models import AnalysisResult, ProjectBrief
from briefs.tests.factories import make_brief, make_user


class ProjectBriefModelTests(TestCase):
    def test_uuid_and_terminal_state(self):
        brief = make_brief(make_user())

        self.assertEqual(str(brief), brief.title)
        self.assertEqual(brief.id.version, 4)
        self.assertFalse(brief.is_terminal)

        brief.status = ProjectBrief.Status.COMPLETED
        self.assertTrue(brief.is_terminal)

    def test_analysis_is_one_to_one(self):
        brief = make_brief(make_user())
        values = {
            "summary": "Une synthèse.",
            "objectives": ["Un objectif"],
            "deliverables": ["Un livrable"],
            "risks": ["Un risque"],
            "next_steps": ["Une étape"],
        }
        AnalysisResult.objects.create(brief=brief, **values)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AnalysisResult.objects.create(brief=brief, **values)

    def test_deleting_user_cascades_to_briefs_and_analysis(self):
        user = make_user()
        brief = make_brief(user)
        AnalysisResult.objects.create(
            brief=brief,
            summary="Une synthèse.",
            objectives=["Un objectif"],
            deliverables=["Un livrable"],
            risks=["Un risque"],
            next_steps=["Une étape"],
        )

        user.delete()

        self.assertFalse(ProjectBrief.objects.filter(pk=brief.pk).exists())
        self.assertFalse(AnalysisResult.objects.exists())
