from rest_framework import serializers

from .models import GeneratedDraft


class GeneratedDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDraft
        fields = ["id", "job", "kind", "source_documents", "prompt_question", "content", "created_at"]
        read_only_fields = fields


class GenerateRequestSerializer(serializers.Serializer):
    """Shared input shape for the tailor-cv / cover-letter / qa actions.

    Both limits below exist because this data goes straight into an
    Anthropic API call (see aiassist/service.py) - unbounded input here is
    real API cost and can push a prompt past the model's context window,
    not just a form-validation nicety.
    """

    # Selecting every document you own into one call isn't a realistic
    # workflow - a CV, maybe a cert or two, a project write-up covers it.
    document_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list, max_length=10
    )
    question = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
