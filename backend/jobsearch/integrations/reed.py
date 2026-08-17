"""Reed.co.uk job search integration.

UK-only, but free and doesn't require salary data to be present to
return results, so it's a good complement to Adzuna for UK depth.
Get a free API key at https://www.reed.co.uk/developers.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

from .base import ExternalJob, raise_clean_request_error

_SEARCH_URL = "https://www.reed.co.uk/api/1.0/search"

_JOB_TYPE_PARAM = {
    "fulltime": "fullTime",
    "parttime": "partTime",
    "contract": "contract",
    "temporary": "temp",
}


class ReedIntegration:
    source_name = "reed"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.REED_API_KEY

    def _search_one(self, keyword: str, location: str, job_type: str) -> list[ExternalJob]:
        params = {
            "keywords": keyword,
            "resultsToTake": 50,
        }
        if location and location.lower() != "remote":
            params["locationName"] = location
        param_name = _JOB_TYPE_PARAM.get(job_type)
        if param_name:
            params[param_name] = "true"

        try:
            response = requests.get(_SEARCH_URL, params=params, auth=(self.api_key, ""), timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise_clean_request_error(exc)
        payload = response.json()

        results = []
        for item in payload.get("results", []):
            # Reed's search endpoint (unlike its per-job Details endpoint)
            # returns raw minimumSalary/maximumSalary with no currency or
            # period field - a posting could be annual, hourly, or daily
            # and there's no way to tell from this response. Flag anything
            # implausibly low as ambiguous rather than silently presenting
            # it as if it were annual.
            salary_min = item.get("minimumSalary")
            salary_max = item.get("maximumSalary")
            compensation = ""
            if salary_min and salary_max:
                compensation = f"GBP {salary_min:.0f} - {salary_max:.0f}"
            elif salary_min:
                compensation = f"GBP {salary_min:.0f}+"
            if compensation and salary_max is not None and salary_max < 1000:
                compensation += " (period not stated by Reed - may be hourly/daily, not annual)"

            results.append(
                ExternalJob(
                    external_id=str(item.get("jobId", "")),
                    title=item.get("jobTitle", ""),
                    company=item.get("employerName", ""),
                    location=item.get("locationName", ""),
                    description=item.get("jobDescription", ""),
                    url=item.get("jobUrl", ""),
                    compensation_raw=compensation,
                )
            )
        return results

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        if country_code.upper() != "GB":
            return []  # Reed only covers the UK - not an error, just no results

        if not self.api_key:
            raise RuntimeError(
                "REED_API_KEY is not set. Get a free key at "
                "https://www.reed.co.uk/developers and add it to your .env."
            )

        # One search per keyword phrase, merged - see the comment in
        # AdzunaIntegration.search() for why joining keywords into a
        # single query breaks matching. Run them concurrently rather than
        # one after another - a profile can have many keywords, and doing
        # them serially (each up to 15s) was slow enough to trip Gunicorn's
        # worker timeout on Railway for profiles with a long keyword list.
        keyword_list = keywords or [""]
        with ThreadPoolExecutor(max_workers=min(6, len(keyword_list))) as executor:
            batches = list(executor.map(lambda kw: self._search_one(kw, location, job_type), keyword_list))

        jobs: list[ExternalJob] = []
        seen_ids: set[str] = set()
        for batch in batches:
            for job in batch:
                if job.external_id in seen_ids:
                    continue
                seen_ids.add(job.external_id)
                jobs.append(job)

        return jobs
