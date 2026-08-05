from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import SignUpForm

User = get_user_model()


def signup_data(**overrides):
    data = {
        "username": "marie",
        "first_name": " Marie ",
        "email": "MARIE@example.com",
        "password1": "a-safe-long-password-47",
        "password2": "a-safe-long-password-47",
    }
    data.update(overrides)
    return data


class SignUpFormTests(TestCase):
    def test_form_normalizes_email_and_first_name(self):
        form = SignUpForm(data=signup_data())

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "marie@example.com")
        self.assertEqual(user.first_name, "Marie")

    def test_email_must_be_unique_case_insensitively(self):
        User.objects.create_user(username="existing", email="marie@example.com", password="password-47")

        form = SignUpForm(data=signup_data(username="another"))

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_confirmation_is_validated(self):
        form = SignUpForm(data=signup_data(password2="different-password-47"))

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)
