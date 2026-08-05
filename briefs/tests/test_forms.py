from django.test import SimpleTestCase, override_settings

from briefs.forms import ProjectBriefForm


def valid_form_data(**overrides):
    data = {
        "title": "  Portail   partenaires ",
        "raw_idea": "Créer un portail qui centralise les demandes et documents des partenaires.",
        "audience": "Partenaires revendeurs",
        "constraints": "Responsive et conforme WCAG AA.",
    }
    data.update(overrides)
    return data


class ProjectBriefFormTests(SimpleTestCase):
    def test_valid_form_normalizes_text(self):
        form = ProjectBriefForm(data=valid_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["title"], "Portail partenaires")

    def test_short_idea_is_rejected(self):
        form = ProjectBriefForm(data=valid_form_data(raw_idea="Trop court"))

        self.assertFalse(form.is_valid())
        self.assertIn("raw_idea", form.errors)

    @override_settings(AI_MAX_INPUT_CHARS=60)
    def test_total_ai_input_limit_is_enforced(self):
        form = ProjectBriefForm(data=valid_form_data())

        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())
