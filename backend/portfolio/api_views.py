from rest_framework import viewsets

from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """CRUD for the caller's own portfolio documents.

    Standard ModelViewSet - list/create at /api/portfolio/documents/,
    retrieve/update/delete at /api/portfolio/documents/<id>/.
    """

    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
