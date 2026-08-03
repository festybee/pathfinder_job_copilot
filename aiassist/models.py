from django.db import models

from jobsearch.models import Job
from portfolio.models import Document


class GeneratedDraft(models.Model):
    """A saved AI output (tailored CV, cover letter, or Q&A answer) tied to
    a specific job, with a record of exactly which portfolio documents it
    was grounded in - so you can tell why it says what it says."""

    class Kind(models.TextChoices):
        CV = "cv", "Tailored CV"
        COVER_LETTER = "cover_letter", "Cover letter"
        QA = "qa", "Application Q&A"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="drafts")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    source_documents = models.ManyToManyField(Document, blank=True)
    prompt_question = models.TextField(blank=True, help_text="Only set for Q&A drafts")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} for {self.job}"
