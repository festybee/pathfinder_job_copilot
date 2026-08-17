from django.contrib import admin

from .models import CriteriaProfile, Job, SearchRun, SponsorRegisterEntry, ThresholdRow


class ThresholdRowInline(admin.TabularInline):
    model = ThresholdRow
    extra = 1


@admin.register(CriteriaProfile)
class CriteriaProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "keywords", "country_code", "salary_mode", "is_active"]
    inlines = [ThresholdRowInline]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "owner", "source", "status", "sponsor_status", "threshold_pass"]
    list_filter = ["source", "status", "sponsor_status", "threshold_pass"]
    search_fields = ["title", "company"]


@admin.register(SearchRun)
class SearchRunAdmin(admin.ModelAdmin):
    """Admin-only log of every 'Run search now' click - lets you spot a
    consistently flaky/rate-limited source without exposing source names
    (Adzuna/Reed/JSearch) to end users, who see only job counts."""

    list_display = [
        "created_at",
        "owner",
        "profile_name",
        "new_jobs",
        "skipped_below_threshold",
        "skipped_duplicate",
        "had_warnings",
    ]
    list_filter = ["owner"]
    search_fields = ["owner__username", "profile_name", "warnings"]
    readonly_fields = [
        "owner",
        "profile",
        "profile_name",
        "new_jobs",
        "skipped_below_threshold",
        "skipped_duplicate",
        "warnings",
        "created_at",
    ]

    @admin.display(boolean=True, description="Had warnings")
    def had_warnings(self, obj):
        return obj.had_warnings

    def has_add_permission(self, request):
        return False  # these are only ever created by a search run, never by hand


@admin.register(SponsorRegisterEntry)
class SponsorRegisterEntryAdmin(admin.ModelAdmin):
    list_display = ["organisation_name", "town_city", "rating", "route", "synced_at"]
    search_fields = ["organisation_name", "organisation_name_normalized"]
    list_filter = ["route"]
