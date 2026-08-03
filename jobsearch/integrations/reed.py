"""Reed.co.uk job search integration.

UK-only, but free and doesn't require salary data to be present to
return results, so it's a good complement to Adzuna for UK depth.
Get a free API key at https://www.reed.co.uk/developers.
"""
from __future__ import annotations

import requests
from django.conf import settings

from .base import ExternalJob

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

        params = {
            "keywords": " ".join(keywords),
            "resultsToTake": 50,
        }
        if location and location.lower() != "remote":
            params["locationName"] = location
        param_name = _JOB_TYPE_PARAM.get(job_type)
        if param_name:
            params[param_name] = "true"

        response = requests.get(
            _SEARCH_URL, params=params, auth=(self.api_key, ""), timeout=15
        )
        response.raise_for_status()
        payload = response.json()

        jobs = []
        for item in payload.get("results", []):
            salary_min = item.get("minimumSalary")
            salary_max = item.get("maximumSalary")
            compensation = ""
            if salary_min and salary_max:
                compensation = f"{salary_min:.0f} - {salary_max:.0f}"
            elif salary_min:
                compensation = f"{salary_min:.0f}+"

            jobs.append(
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
        return jobs
