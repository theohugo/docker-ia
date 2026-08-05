"""Keep a profile available for every Django user."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="accounts.ensure_user_profile")
def ensure_user_profile(sender, instance, created: bool, **kwargs) -> None:
    if created:
        Profile.objects.create(user=instance)
        return
    Profile.objects.get_or_create(user=instance)
