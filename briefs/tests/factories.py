from django.contrib.auth import get_user_model

from briefs.models import ProjectBrief

User = get_user_model()


def make_user(username="owner"):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="password-47",
    )


def make_brief(user, **overrides):
    values = {
        "title": "Refonte de l'espace client",
        "raw_idea": "Simplifier le suivi des demandes pour réduire les appels au support.",
        "audience": "Clients professionnels et équipe support",
        "constraints": "Livraison en huit semaines, accessibilité WCAG AA.",
        "status": ProjectBrief.Status.QUEUED,
        "provider": "demo",
        "model": "demo-cadria-v1",
    }
    values.update(overrides)
    return ProjectBrief.objects.create(user=user, **values)
