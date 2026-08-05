from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignUpViewTests(TestCase):
    def test_signup_page_is_public(self):
        response = self.client.get(reverse("accounts:signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form", html=False)

    def test_valid_signup_creates_authenticated_user_and_profile(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new-user",
                "first_name": "Nora",
                "email": "nora@example.com",
                "password1": "a-safe-long-password-47",
                "password2": "a-safe-long-password-47",
            },
        )

        user = User.objects.get(username="new-user")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(user.profile.user_id, user.pk)

    def test_authenticated_user_is_redirected_from_signup(self):
        user = User.objects.create_user(username="member", password="password-47")
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:signup"))

        self.assertRedirects(response, reverse("dashboard"))
