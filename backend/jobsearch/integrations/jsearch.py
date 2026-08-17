"""JSearch (via OpenWeb Ninja) job search integration.

JSearch doesn't source jobs itself - it aggregates Google for Jobs, which
pulls listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter, and most
other public job boards into one feed. That's the workaround most small
job-search products use for broad coverage, since LinkedIn/Indeed don't
offer open APIs to third-party developers.

Free tier: 200 requests/month, then $25/mo for 10,000. Get a key at
https://www.openwebninja.com/api/jsearch (also available via RapidAPI).

Response shape (confirmed against OpenWeb Ninja's docs): the job list is
nested under data.jobs, not data itself -
    {"status": "OK", "request_id": "...", "data": {"jobs": [...], "cursor": "..."}}
Salary fields are only populated when the employer explicitly included
pay in the posting - most postings won't have compensation_raw set, and
that's expected, not a bug.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

from .base import ExternalJob, raise_clean_request_error

_SEARCH_URL = "https://api.openwebninja.com/jsearch/search-v2"

# JSearch's own "country" request param doesn't reliably restrict results
# to that country in practice - e.g. a country="gb" search can still
# return US postings. So in addition to sending the param (harmless, may
# help narrow results somewhat), we also filter client-side using each
# result's own job_country field. Only maps countries this app's
# CriteriaProfile.country_code actually supports; a country_code with no
# entry here is left unfiltered rather than silently dropping everything.
_COUNTRY_NAME_VARIANTS = {
    "GB": {"united kingdom", "uk", "gb", "england", "scotland", "wales", "northern ireland"},
    "US": {"united states", "usa", "us", "united states of america"},
    "CA": {"canada", "ca"},
    "AU": {"australia", "au"},
    "NZ": {"new zealand", "nz"},
    "IE": {"ireland", "ie"},
    "DE": {"germany", "de"},
    "FR": {"france", "fr"},
    "NL": {"netherlands", "nl"},
    "IN": {"india", "in"},
    "SG": {"singapore", "sg"},
}


class JSearchIntegration:
    source_name = "jsearch"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.JSEARCH_API_KEY

    def _search_one(
        self, keyword: str, location: str, country_code: str, is_remote: bool
    ) -> list[ExternalJob]:
        # JSearch takes one free-text query rather than separate
        # keyword/location params - docs recommend folding location into
        # the query text for better matches.
        query = keyword
        if location and not is_remote:
            query = f"{keyword} in {location}".strip() if keyword else location

        params = {"query": query.strip() or location or "jobs"}
        if country_code:
            params["country"] = country_code.lower()
        if is_remote:
            params["work_from_home"] = "true"

        try:
            response = requests.get(
                _SEARCH_URL,
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise_clean_request_error(exc)
        payload = response.json()

        expected_country_names = _COUNTRY_NAME_VARIANTS.get(country_code.upper()) if country_code else None

        results = []
        for item in (payload.get("data") or {}).get("jobs", []):
            external_id = str(item.get("job_id", ""))
            if not external_id:
                continue

            # Reject results the API returned for a clearly different
            # country than requested - see _COUNTRY_NAME_VARIANTS above.
            item_country = (item.get("job_country") or "").strip().lower()
            if expected_country_names and item_country and item_country not in expected_country_names:
                continue

            salary_min = item.get("job_min_salary")
            salary_max = item.get("job_max_salary")
            period = (item.get("job_salary_period") or "").upper()
            compensation = ""
            if salary_min and salary_max:
                compensation = f"{salary_min:.0f} - {salary_max:.0f}"
            elif salary_min:
                compensation = f"{salary_min:.0f}+"
            if compensation:
                if period and period != "YEAR":
                    compensation += f" per {period.lower()}"
                elif not period and salary_max is not None and salary_max < 1000:
                    compensation += " (period not stated - may not be annual)"

            location_str = item.get("job_location") or ", ".join(
                filter(None, [item.get("job_city"), item.get("job_state"), item.get("job_country")])
            )

            results.append(
                ExternalJob(
                    external_id=external_id,
                    title=item.get("job_title", ""),
                    company=item.get("employer_name", ""),
                    location=location_str,
                    description=item.get("job_description", ""),
                    url=item.get("job_apply_link", ""),
                    compensation_raw=compensation,
                )
            )
        return results

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        if not self.api_key:
            raise RuntimeError(
                "JSEARCH_API_KEY is not set. Get a free key at "
                "https://www.openwebninja.com/api/jsearch and add it to your .env."
            )

        is_remote = bool(location) and location.lower() == "remote"

        # One request per keyword phrase, run concurrently rather than one
        # after another - a profile can have many keywords, and JSearch in
        # particular (it proxies Google for Jobs) is the slowest of the
        # three sources. Doing these serially was slow enough to trip
        # Gunicorn's worker timeout on Railway for profiles with a long
        # keyword list.
        keyword_list = keywords or [""]
        with ThreadPoolExecutor(max_workers=min(6, len(keyword_list))) as executor:
            batches = list(
                executor.map(
                    lambda kw: self._search_one(kw, location, country_code, is_remote), keyword_list
                )
            )

        jobs: list[ExternalJob] = []
        seen_ids: set[str] = set()
        for batch in batches:
            for job in batch:
                if job.external_id in seen_ids:
                    continue
                seen_ids.add(job.external_id)
                jobs.append(job)

        return jobs
