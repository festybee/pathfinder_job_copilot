from rest_framework import serializers

from .models import GeneratedDraft


class GeneratedDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDraft
        fields = ["id", "job", "kind", "source_documents", "prompt_question", "content", "created_at"]
        read_only_fields = fields


class GenerateRequestSerializer(serializers.Serializer):
    """Shared input shape for the tailor-cv / cover-letter / qa actions."""

    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    question = serializers.CharField(required=False, allow_blank=True, default="")
