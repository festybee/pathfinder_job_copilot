from django.contrib import admin

from .models import CriteriaProfile, Job, SponsorRegisterEntry, ThresholdRow


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


@admin.register(SponsorRegisterEntry)
class SponsorRegisterEntryAdmin(admin.ModelAdmin):
    list_display = ["organisation_name", "town_city", "rating", "route", "synced_at"]
    search_fields = ["organisation_name", "organisation_name_normalized"]
    list_filter = ["route"]
