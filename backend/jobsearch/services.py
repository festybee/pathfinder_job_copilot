"""Glue between CriteriaProfile, the integrations, and the Job tracker."""
from __future__ import annotations

import re

from .integrations.adzuna import AdzunaIntegration
from .integrations.base import ExternalJob
from .integrations.jsearch import JSearchIntegration
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
    results_by_source: dict[str, list[ExternalJob]] = {}
    warnings: list[str] = []

    for source_key, display_name, integration in [
        (Job.Source.ADZUNA, "Adzuna", AdzunaIntegration()),
        (Job.Source.REED, "Reed", ReedIntegration()),
        (Job.Source.JSEARCH, "JSearch", JSearchIntegration()),
    ]:
        try:
            role_results = integration.search(
                keywords=keywords,
                location=profile.location,
                country_code=profile.country_code,
                job_type=profile.job_type,
            )
            combined = list(role_results)

            if profile.include_sponsorship_keyword:
                # Separate pass, not merged into the keyword list - "visa
                # sponsorship" on its own matches whatever mentions it
                # (support worker, care assistant, ...) regardless of role.
                # Only keep those results if they're ALSO relevant to one
                # of the actual role keywords, so this can only add jobs
                # you'd want, never pollute the tracker with off-role
                # results. See sponsor_register.check_sponsor_licence()
                # for the reliable (non-keyword-based) sponsorship check.
                sponsorship_results = integration.search(
                    keywords=["visa sponsorship"],
                    location=profile.location,
                    country_code=profile.country_code,
                    job_type=profile.job_type,
                )
                seen_ids = {job.external_id for job in combined}
                for job in sponsorship_results:
                    if job.external_id in seen_ids:
                        continue
                    title_lower = job.title.lower()
                    if any(kw.lower() in title_lower for kw in keywords):
                        combined.append(job)
                        seen_ids.add(job.external_id)

            results_by_source[source_key] = combined
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
    # Below this, a figure is almost certainly not a real UK annual salary
    # (hourly/daily/weekly rate misread as one) - treat as unparseable
    # rather than comparing it against a thousands-scale threshold, which
    # would silently produce a nonsense pass/fail. See the comment in
    # ReedIntegration.search() - this guards against exactly that source.
    if low_salary is None or low_salary < 1000:
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
