from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from jobsearch.models import Job

from . import service
from .forms import DocumentSelectForm, QuestionForm
from .models import GeneratedDraft


def _get_owned_job(request, job_id):
    return get_object_or_404(Job, pk=job_id, owner=request.user)


@login_required
def tailor_cv(request, job_id):
    job = _get_owned_job(request, job_id)

    if request.method == "POST":
        form = DocumentSelectForm(request.POST, owner=request.user)
        if form.is_valid():
            documents = list(form.cleaned_data["documents"])
            try:
                content = service.tailor_cv(job, documents)
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"Couldn't generate a draft: {exc}")
            else:
                draft = GeneratedDraft.objects.create(job=job, kind=GeneratedDraft.Kind.CV, content=content)
                draft.source_documents.set(documents)
    else:
        form = DocumentSelectForm(owner=request.user)

    drafts = job.drafts.filter(kind=GeneratedDraft.Kind.CV)
    return render(request, "aiassist/generate.html", {
        "job": job, "form": form, "drafts": drafts, "title": "Tailor CV",
    })


@login_required
def cover_letter(request, job_id):
    job = _get_owned_job(request, job_id)

    if request.method == "POST":
        form = DocumentSelectForm(request.POST, owner=request.user)
        if form.is_valid():
            documents = list(form.cleaned_data["documents"])
            try:
                content = service.draft_cover_letter(job, documents)
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"Couldn't generate a draft: {exc}")
            else:
                draft = GeneratedDraft.objects.create(
                    job=job, kind=GeneratedDraft.Kind.COVER_LETTER, content=content
                )
                draft.source_documents.set(documents)
    else:
        form = DocumentSelectForm(owner=request.user)

    drafts = job.drafts.filter(kind=GeneratedDraft.Kind.COVER_LETTER)
    return render(request, "aiassist/generate.html", {
        "job": job, "form": form, "drafts": drafts, "title": "Cover letter",
    })


@login_required
def qa(request, job_id):
    job = _get_owned_job(request, job_id)

    if request.method == "POST":
        form = QuestionForm(request.POST, owner=request.user)
        if form.is_valid():
            documents = list(form.cleaned_data["documents"])
            question = form.cleaned_data["question"]
            try:
                content = service.answer_question(job, documents, question)
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"Couldn't generate an answer: {exc}")
            else:
                draft = GeneratedDraft.objects.create(
                    job=job, kind=GeneratedDraft.Kind.QA, content=content, prompt_question=question
                )
                draft.source_documents.set(documents)
            form = QuestionForm(owner=request.user)
    else:
        form = QuestionForm(owner=request.user)

    drafts = job.drafts.filter(kind=GeneratedDraft.Kind.QA)
    return render(request, "aiassist/qa.html", {"job": job, "form": form, "drafts": drafts})
