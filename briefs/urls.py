from django.urls import path

from . import views

app_name = "briefs"

urlpatterns = [
    path("new/", views.create, name="create"),
    path("<uuid:pk>/", views.detail, name="detail"),
    path("<uuid:pk>/status/", views.status, name="status"),
]
