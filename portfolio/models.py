from django.conf import settings
from django.db import models


class Document(models.Model):
    """A piece of the user's portfolio: a CV, cert, project write-up, etc.

    The AI layer (aiassist) only ever grounds drafts in Documents the user
    explicitly ticks - nothing gets pulled in silently.
    """

    class DocType(models.TextChoices):
        CV = "cv", "CV / Resume"
        CERTIFICATE = "certificate", "Certificate"
        PROJECT = "project", "Project write-up"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    tags = models.CharField(
        max_length=300, blank=True, help_text="Comma-separated, e.g. 'python, sql, agile'"
    )
    body_text = models.TextField(
        blank=True, help_text="Pasted text content - what the AI layer actually reads."
    )
    file = models.FileField(upload_to="portfolio/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"

    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]
