from django.contrib import admin

from .models import CriteriaProfile, Job, ThresholdRow


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
