"""Match job employer names against the UK government's register of
licensed Worker/Temporary Worker sponsors.

This is the actual reliable sponsorship signal (as opposed to the
"visa sponsorship" keyword heuristic in services.run_search) - but it's
still not perfect: company names in job postings often differ slightly
from their registered legal name (trading names, punctuation, missing
"Ltd"/"Limited"), so a non-match does NOT mean "not a sponsor", only
"couldn't confirm". We only ever auto-set CONFIRMED on a match; we never
auto-set NO.
"""
from __future__ import annotations

import re

from .models import Job, SponsorRegisterEntry

_SUFFIX_RE = re.compile(
    r"\b(LTD|LIMITED|LLP|LLC|PLC|INC|CIC|CO|COMPANY|GROUP|HOLDINGS?)\b"
)
_TRADING_AS_RE = re.compile(r"\bT/?A\b.*$", re.IGNORECASE)  # "Foo Ltd T/a Bar" -> keep "Foo Ltd" part
_NON_WORD_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """Collapse a company name to a rough matching key: uppercase, strip
    punctuation and common legal suffixes/trading-as text, collapse
    whitespace. Not a perfect match key, but good enough to catch the
    common "Foo Ltd" vs "FOO LIMITED" vs "Foo LTD " variance."""
    if not name:
        return ""
    name = _TRADING_AS_RE.sub("", name)
    name = name.upper()
    name = _NON_WORD_RE.sub(" ", name)
    name = _SUFFIX_RE.sub(" ", name)
    name = _WHITESPACE_RE.sub(" ", name).strip()
    return name


def check_sponsor_licence(company_name: str) -> bool | None:
    """True if company_name matches a register entry, None if we can't
    tell (no confident match either way - never returns False)."""
    normalized = normalize_company_name(company_name)
    if not normalized:
        return None

    if SponsorRegisterEntry.objects.filter(organisation_name_normalized=normalized).exists():
        return True
    return None


def apply_sponsor_check(job: Job) -> bool:
    """Check job.company against the register and, on a match, set
    sponsor_status to CONFIRMED. Returns True if it was updated. Never
    downgrades an existing status (e.g. won't overwrite a manual "No")."""
    if job.sponsor_status == Job.SponsorStatus.CONFIRMED:
        return False

    if check_sponsor_licence(job.company):
        job.sponsor_status = Job.SponsorStatus.CONFIRMED
        job.save(update_fields=["sponsor_status"])
        return True
    return False
