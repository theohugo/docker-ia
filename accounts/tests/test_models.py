from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Profile

User = get_user_model()


class ProfileTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(username="ada", password="correct horse battery staple")

        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_string_prefers_display_name(self):
        user = User.objects.create_user(username="grace", password="correct horse battery staple")
        user.profile.display_name = "Grace H."
        user.profile.save()

        self.assertEqual(str(user.profile), "Grace H.")

    def test_missing_profile_is_repaired_when_user_is_saved(self):
        user = User.objects.create_user(username="linus", password="correct horse battery staple")
        user.profile.delete()

        user.first_name = "Linus"
        user.save()

        self.assertTrue(Profile.objects.filter(user=user).exists())
