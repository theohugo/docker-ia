"""Root URL configuration for CadrIA."""

from django.contrib import admin
from django.urls import include, path

from briefs.views import dashboard

from .views import HealthView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("health/", HealthView.as_view(), name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", dashboard, name="dashboard"),
    path("briefs/", include("briefs.urls")),
]
