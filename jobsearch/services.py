"""Glue between CriteriaProfile, the integrations, and the Job tracker."""
from __future__ import annotations

import re

from .integrations.adzuna import AdzunaIntegration
from .integrations.base import ExternalJob
from .integrations.reed import ReedIntegration
from .models import CriteriaProfile, Job, ThresholdRow
from .sponsor_register import apply_sponsor_check

_SALARY_NUM_RE = re.compile(r"[\d,]{4,}")


def run_search(profile: CriteriaProfile) -> tuple[dict[str, list[ExternalJob]], list[str]]:
    """Search all available sources for this profile's criteria.

    Returns (results_by_source, warnings). results_by_source keys match
    Job.Source values ("adzuna", "reed") so callers can save each batch
    with the right source tag. warnings hold any per-source errors (e.g.
    missing API key) so one broken source doesn't fail the whole search.
    """
    keywords = profile.keyword_list()
    if profile.include_sponsorship_keyword:
        # Extra, independent search term - not ANDed with the role keywords,
        # since "data analyst visa sponsorship" would rarely match anything.
        # Weak signal: surfaces postings that happen to mention sponsorship,
        # nothing more. See sponsor_register.check_sponsor_licence() for the
        # actual reliable check.
        keywords = keywords + ["visa sponsorship"]

    results_by_source: dict[str, list[ExternalJob]] = {}
    warnings: list[str] = []

    for source_key, display_name, integration in [
        (Job.Source.ADZUNA, "Adzuna", AdzunaIntegration()),
        (Job.Source.REED, "Reed", ReedIntegration()),
    ]:
        try:
            results_by_source[source_key] = integration.search(
                keywords=keywords,
                location=profile.location,
                country_code=profile.country_code,
                job_type=profile.job_type,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{display_name}: {exc}")

    return results_by_source, warnings


def _extract_low_salary(compensation_raw: str) -> int | None:
    numbers = [int(n.replace(",", "")) for n in _SALARY_NUM_RE.findall(compensation_raw)]
    return min(numbers) if numbers else None


def _matching_threshold_row(job_title: str, rows: list[ThresholdRow]) -> ThresholdRow | None:
    title_lower = job_title.lower()
    for row in rows:
        if row.keyword_match.lower() in title_lower:
            return row
    return None


def evaluate_threshold(job: Job) -> None:
    """Set job.threshold_pass based on the profile's salary_mode. Saves the job."""
    profile = job.profile
    if profile is None:
        return

    low_salary = _extract_low_salary(job.compensation_raw)
    if low_salary is None:
        job.threshold_pass = None
        job.save(update_fields=["threshold_pass"])
        return

    if profile.salary_mode == CriteriaProfile.SalaryMode.FLAT_MINIMUM:
        threshold = profile.flat_minimum_salary
    else:
        row = _matching_threshold_row(job.title, list(profile.threshold_rows.all()))
        threshold = row.threshold_amount if row else None

    job.threshold_pass = (low_salary >= threshold) if threshold is not None else None
    job.save(update_fields=["threshold_pass"])


def save_results(profile: CriteriaProfile, source_name: str, external_jobs: list[ExternalJob]) -> int:
    """Upsert ExternalJob results as Job rows. Returns count of newly created jobs."""
    created = 0
    for ext in external_jobs:
        job, was_created = Job.objects.get_or_create(
            owner=profile.owner,
            source=source_name,
            external_id=ext.external_id,
            defaults={
                "profile": profile,
                "title": ext.title,
                "company": ext.company,
                "location": ext.location,
                "description": ext.description,
                "url": ext.url,
                "compensation_raw": ext.compensation_raw,
            },
        )
        if was_created:
            created += 1
            evaluate_threshold(job)
            apply_sponsor_check(job)  # no-op if the register hasn't been synced yet

    return created
