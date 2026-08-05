from django.contrib import admin

from .models import AnalysisResult, GenerationEvent, ProjectBrief


class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class GenerationEventInline(admin.TabularInline):
    model = GenerationEvent
    extra = 0
    can_delete = False
    readonly_fields = ("event_type", "provider", "model", "message", "metadata", "created_at")


@admin.register(ProjectBrief)
class ProjectBriefAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "provider", "model", "created_at")
    list_filter = ("status", "provider", "created_at")
    search_fields = ("title", "raw_idea", "user__username", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (AnalysisResultInline, GenerationEventInline)


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("brief", "tokens_used", "duration_ms", "created_at")
    search_fields = ("brief__title", "summary")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GenerationEvent)
class GenerationEventAdmin(admin.ModelAdmin):
    list_display = ("brief", "event_type", "provider", "model", "created_at")
    list_filter = ("event_type", "provider")
    search_fields = ("brief__title", "message")
    readonly_fields = ("created_at",)
