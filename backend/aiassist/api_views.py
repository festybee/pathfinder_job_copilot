from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from jobsearch.models import Job
from portfolio.models import Document

from . import service
from .models import GeneratedDraft
from .serializers import GenerateRequestSerializer, GeneratedDraftSerializer


def _get_owned_job(request, job_id):
    return get_object_or_404(Job, pk=job_id, owner=request.user)


def _get_owned_documents(request, document_ids):
    return list(Document.objects.filter(owner=request.user, pk__in=document_ids))


def _run_generation(request, job_id, kind, generate_fn, needs_question=False):
    job = _get_owned_job(request, job_id)
    req = GenerateRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    documents = _get_owned_documents(request, req.validated_data["document_ids"])
    question = req.validated_data["question"]

    if needs_question and not question.strip():
        return Response({"detail": "question is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if needs_question:
            content = generate_fn(job, documents, question)
        else:
            content = generate_fn(job, documents)
    except Exception as exc:  # noqa: BLE001
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    draft = GeneratedDraft.objects.create(
        job=job,
        kind=kind,
        content=content,
        prompt_question=question if needs_question else "",
    )
    draft.source_documents.set(documents)
    return Response(GeneratedDraftSerializer(draft).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def tailor_cv(request, job_id):
    return _run_generation(request, job_id, GeneratedDraft.Kind.CV, service.tailor_cv)


@api_view(["POST"])
def cover_letter(request, job_id):
    return _run_generation(request, job_id, GeneratedDraft.Kind.COVER_LETTER, service.draft_cover_letter)


@api_view(["POST"])
def qa(request, job_id):
    return _run_generation(
        request, job_id, GeneratedDraft.Kind.QA, service.answer_question, needs_question=True
    )


@api_view(["GET"])
def drafts(request, job_id):
    job = _get_owned_job(request, job_id)
    qs = job.drafts.all()
    kind = request.query_params.get("kind")
    if kind:
        qs = qs.filter(kind=kind)
    return Response(GeneratedDraftSerializer(qs, many=True).data)
