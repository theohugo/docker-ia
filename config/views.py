"""Small project-level views."""

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


class HealthView(View):
    """Report whether the application can reach its primary database."""

    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return JsonResponse({"status": "unhealthy", "database": "unavailable"}, status=503)
        return JsonResponse({"status": "ok", "database": "ok"})
