from django.contrib import admin

from .models import GeneratedDraft


@admin.register(GeneratedDraft)
class GeneratedDraftAdmin(admin.ModelAdmin):
    list_display = ["job", "kind", "created_at"]
    list_filter = ["kind"]
