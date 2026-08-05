"""Input validation for a new project brief."""

from django import forms
from django.conf import settings

from .models import ProjectBrief


class ProjectBriefForm(forms.ModelForm):
    class Meta:
        model = ProjectBrief
        fields = ("title", "raw_idea", "audience", "constraints")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "autocomplete": "off",
                    "placeholder": "Ex. Lancer une newsletter métier…",
                }
            ),
            "raw_idea": forms.Textarea(
                attrs={
                    "autocomplete": "off",
                    "placeholder": "Décrivez le problème, votre intuition et le résultat espéré…",
                    "rows": 7,
                }
            ),
            "audience": forms.Textarea(
                attrs={
                    "autocomplete": "off",
                    "placeholder": "Ex. Indépendants depuis moins de 3 ans…",
                    "rows": 4,
                }
            ),
            "constraints": forms.Textarea(
                attrs={
                    "autocomplete": "off",
                    "placeholder": "Ex. Budget, délai, outils imposés…",
                    "rows": 4,
                }
            ),
        }
        help_texts = {
            "title": "Un nom court pour retrouver facilement ce brief.",
            "raw_idea": "Décrivez le contexte, le besoin et le résultat attendu.",
            "audience": "Qui utilisera ou recevra ce projet ?",
            "constraints": "Budget, délai, ton, canaux ou exigences particulières.",
        }

    def clean_title(self) -> str:
        title = " ".join(self.cleaned_data["title"].split())
        if len(title) < 3:
            raise forms.ValidationError("Le titre doit contenir au moins 3 caractères.")
        return title

    def clean_raw_idea(self) -> str:
        value = self.cleaned_data["raw_idea"].strip()
        if len(value) < 20:
            raise forms.ValidationError("Décrivez votre idée en au moins 20 caractères.")
        return value

    def clean_audience(self) -> str:
        value = self.cleaned_data["audience"].strip()
        if len(value) < 3:
            raise forms.ValidationError("Précisez le public cible.")
        return value

    def clean_constraints(self) -> str:
        return self.cleaned_data["constraints"].strip()

    def clean(self):
        cleaned_data = super().clean()
        max_chars = settings.AI_MAX_INPUT_CHARS
        total_chars = sum(
            len(cleaned_data.get(field, "")) for field in ("title", "raw_idea", "audience", "constraints")
        )
        if total_chars > max_chars:
            raise forms.ValidationError(
                f"Le brief dépasse la limite de {max_chars:,} caractères.".replace(",", " ")
            )
        return cleaned_data
