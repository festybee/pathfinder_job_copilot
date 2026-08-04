"""JSearch (via OpenWeb Ninja) job search integration.

JSearch doesn't source jobs itself - it aggregates Google for Jobs, which
pulls listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter, and most
other public job boards into one feed. That's the workaround most small
job-search products use for broad coverage, since LinkedIn/Indeed don't
offer open APIs to third-party developers.

Free tier: 200 requests/month, then $25/mo for 10,000. Get a key at
https://www.openwebninja.com/api/jsearch (also available via RapidAPI).

Note: OpenWeb Ninja's docs page is JS-rendered and I couldn't fully load
it, so this is built from their published sample response data (a
per-job object schema shown for a job-detail lookup) plus documented
query parameters, not a live test against search-v2 specifically. If
field names don't line up with what you actually get back, print/inspect
response.json() and adjust the parsing below - the shape may differ
slightly for search results vs. the single-job sample.
"""
from __future__ import annotations

import requests
from django.conf import settings

from .base import ExternalJob

_SEARCH_URL = "https://api.openwebninja.com/jsearch/search-v2"


class JSearchIntegration:
    source_name = "jsearch"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.JSEARCH_API_KEY

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        if not self.api_key:
            raise RuntimeError(
                "JSEARCH_API_KEY is not set. Get a free key at "
                "https://www.openwebninja.com/api/jsearch and add it to your .env."
            )

        is_remote = bool(location) and location.lower() == "remote"

        jobs: list[ExternalJob] = []
        seen_ids: set[str] = set()

        for keyword in keywords or [""]:
            # JSearch takes one free-text query rather than separate
            # keyword/location params - docs recommend folding location
            # into the query text for better matches.
            query = keyword
            if location and not is_remote:
                query = f"{keyword} in {location}".strip() if keyword else location

            params = {"query": query.strip() or location or "jobs"}
            if country_code:
                params["country"] = country_code.lower()
            if is_remote:
                params["work_from_home"] = "true"

            response = requests.get(
                _SEARCH_URL,
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()

            for item in payload.get("data", []):
                external_id = str(item.get("job_id", ""))
                if not external_id or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                salary_min = item.get("job_min_salary")
                salary_max = item.get("job_max_salary")
                compensation = ""
                if salary_min and salary_max:
                    compensation = f"{salary_min:.0f} - {salary_max:.0f}"
                elif salary_min:
                    compensation = f"{salary_min:.0f}+"

                location_str = item.get("job_location") or ", ".join(
                    filter(
                        None,
                        [item.get("job_city"), item.get("job_state"), item.get("job_country")],
                    )
                )

                jobs.append(
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

        return jobs
