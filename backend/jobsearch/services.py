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
            # Some sources (Reed in particular) do loose/fuzzy matching
            # server-side and can hand back jobs whose titles don't contain
            # any of the searched keywords at all (e.g. an "IT Support
            # Assistant" posting showing up for a "data analyst" search).
            # Require the title to actually contain one of the keywords -
            # same check already used below for the sponsorship-only pass.
            combined = [
                job for job in role_results if any(kw.lower() in job.title.lower() for kw in keywords)
            ]

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
    low = min(numbers) if numbers else None
    # Below this, a figure is almost certainly not a real UK annual salary
    # (hourly/daily/weekly rate misread as one) - treat as unparseable
    # rather than comparing it against a thousands-scale threshold, which
    # would silently produce a nonsense pass/fail. See the comment in
    # ReedIntegration.search() - this guards against exactly that source.
    if low is not None and low < 1000:
        return None
    return low


def _matching_threshold_row(job_title: str, rows: list[ThresholdRow]) -> ThresholdRow | None:
    title_lower = job_title.lower()
    for row in rows:
        if row.keyword_match.lower() in title_lower:
            return row
    return None


def compute_threshold(profile: CriteriaProfile, title: str, compensation_raw: str) -> bool | None:
    """Whether a job clears its profile's salary rule.

    Returns None when there's no rule to judge this job by yet (going-rate
    mode with no matching keyword row, or flat-minimum mode with no amount
    set) - such jobs are still kept, unevaluated, so new role types remain
    visible and you can add a going-rate row for them.

    Once a rule *does* apply, missing/unparseable salary counts as 0 rather
    than being treated as unevaluated - a job with no stated salary doesn't
    get a free pass on a mandatory threshold.
    """
    if profile.salary_mode == CriteriaProfile.SalaryMode.FLAT_MINIMUM:
        threshold = profile.flat_minimum_salary
    else:
        row = _matching_threshold_row(title, list(profile.threshold_rows.all()))
        threshold = row.threshold_amount if row else None

    if threshold is None:
        return None

    low_salary = _extract_low_salary(compensation_raw)
    effective_salary = low_salary if low_salary is not None else 0
    return effective_salary >= threshold


def _job_fingerprint(title: str, company: str, location: str) -> tuple[str, str, str]:
    return (title.strip().lower(), company.strip().lower(), location.strip().lower())


def existing_fingerprints_for(owner) -> set[tuple[str, str, str]]:
    """(title, company, location) of every job already saved for this
    owner, across all profiles/sources - used to catch recruiter reposts
    (same job, new external_id each time) that the source-level dedup in
    save_results() wouldn't otherwise catch."""
    return {
        _job_fingerprint(j.title, j.company, j.location)
        for j in Job.objects.filter(owner=owner).only("title", "company", "location")
    }


def evaluate_threshold(job: Job) -> None:
    """Recompute + save job.threshold_pass for an already-saved job. Used by
    the purge_below_threshold_jobs management command; new jobs from a
    search are evaluated before they're ever saved (see save_results)."""
    profile = job.profile
    if profile is None:
        job.threshold_pass = None
        job.save(update_fields=["threshold_pass"])
        return
    job.threshold_pass = compute_threshold(profile, job.title, job.compensation_raw)
    job.save(update_fields=["threshold_pass"])


def save_results(
    profile: CriteriaProfile,
    source_name: str,
    external_jobs: list[ExternalJob],
    seen_fingerprints: set[tuple[str, str, str]] | None = None,
) -> tuple[int, int, int]:
    """Upsert ExternalJob results as Job rows.

    A job is skipped entirely - never written to the database - in two
    cases: (1) a salary rule applies to it (a matching going-rate row, or a
    flat minimum) and it doesn't clear it, with missing/unparseable salary
    counting as 0; or (2) it's the same job (by title/company/location) as
    one already saved, which catches recruiter reposts under a new
    external_id that the source+external_id uniqueness wouldn't. Jobs with
    no applicable threshold rule yet are still saved (threshold_pass=None)
    so new role types stay visible.

    `seen_fingerprints` lets a caller share one set across multiple sources
    in the same search, so a duplicate is caught even if two different
    sources return it. Pass None to have this function build it fresh from
    the DB (checked only against jobs already saved before this call).

    Returns (created, skipped_below_threshold, skipped_duplicate).
    """
    if seen_fingerprints is None:
        seen_fingerprints = existing_fingerprints_for(profile.owner)

    created = 0
    skipped = 0
    skipped_duplicate = 0
    for ext in external_jobs:
        fingerprint = _job_fingerprint(ext.title, ext.company, ext.location)
        if fingerprint in seen_fingerprints:
            skipped_duplicate += 1
            continue

        threshold_pass = compute_threshold(profile, ext.title, ext.compensation_raw)
        if threshold_pass is False:
            skipped += 1
            seen_fingerprints.add(fingerprint)
            continue

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
                "threshold_pass": threshold_pass,
            },
        )
        seen_fingerprints.add(fingerprint)
        if was_created:
            created += 1
            apply_sponsor_check(job)  # no-op if the register hasn't been synced yet

    return created, skipped, skipped_duplicate
