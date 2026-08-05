"""Account-related persistence."""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Product-specific information kept alongside Django's built-in user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField("nom affiché", max_length=120, blank=True)
    company = models.CharField("organisation", max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.display_name or self.user.get_full_name() or self.user.get_username()
