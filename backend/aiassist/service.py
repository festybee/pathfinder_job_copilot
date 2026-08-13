"""Thin wrapper around the Anthropic SDK for the three AI-assisted steps:
tailoring a CV, drafting a cover letter, and answering application
questions. Every function is grounded ONLY in the portfolio Documents
passed in - nothing is invented, and nothing pulls in documents the user
didn't explicitly select for this job.
"""
from __future__ import annotations

from django.conf import settings

from jobsearch.models import Job
from portfolio.models import Document

_GROUNDING_RULE = (
    "Only use facts present in the candidate material below. Never invent "
    "employers, dates, skills, or achievements. If the material doesn't "
    "cover something the job asks for, leave it out rather than guessing."
)


def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env before "
            "using the AI assist features."
        )
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _render_documents(documents: list[Document]) -> str:
    if not documents:
        return "(no portfolio documents selected)"
    parts = []
    for doc in documents:
        parts.append(f"--- {doc.title} ({doc.get_doc_type_display()}) ---\n{doc.body_text}")
    return "\n\n".join(parts)


def _render_job(job: Job) -> str:
    return (
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n"
        f"Compensation: {job.compensation_raw or 'not stated'}\n"
        f"Description: {job.description or '(no description saved)'}"
    )


def _complete(system: str, user_prompt: str, max_tokens: int = 700) -> str:
    client = _client()
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    )


def tailor_cv(job: Job, documents: list[Document]) -> str:
    system = (
        "You tailor CVs to specific job postings. Reorder and reframe "
        "existing experience to foreground what's relevant; do not add "
        "anything not present in the source material. "
        f"{_GROUNDING_RULE} Output plain text, ready to paste into a "
        "document - use clear section headings, no markdown syntax."
    )
    user_prompt = f"Job posting:\n{_render_job(job)}\n\nCandidate material:\n{_render_documents(documents)}\n\nProduce a tailored CV for this job."
    return _complete(system, user_prompt, max_tokens=1200)


def draft_cover_letter(job: Job, documents: list[Document]) -> str:
    system = (
        "You write concise, specific cover letters. Under 300 words, no "
        "generic filler, no restating the job posting back at the reader. "
        f"{_GROUNDING_RULE}"
    )
    user_prompt = f"Job posting:\n{_render_job(job)}\n\nCandidate material:\n{_render_documents(documents)}\n\nWrite a cover letter from this candidate for this job."
    return _complete(system, user_prompt, max_tokens=600)


def answer_question(job: Job, documents: list[Document], question: str) -> str:
    system = (
        "You help a candidate answer application form questions truthfully "
        f"and specifically, grounded in their own material. {_GROUNDING_RULE} "
        "If the material doesn't contain enough to answer well, say so "
        "plainly rather than padding with generic statements."
    )
    user_prompt = (
        f"Job posting:\n{_render_job(job)}\n\n"
        f"Candidate material:\n{_render_documents(documents)}\n\n"
        f"Application question: {question}\n\nDraft an answer."
    )
    return _complete(system, user_prompt, max_tokens=500)
