from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "doc_type", "owner", "updated_at"]
    list_filter = ["doc_type"]
    search_fields = ["title", "tags", "body_text"]
