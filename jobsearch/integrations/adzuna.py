"""Adzuna job search integration.

Adzuna has decent multi-country coverage and returns salary data on many
listings, which is what makes the going-rate/threshold check possible.
Free tier requires an app_id + app_key from https://developer.adzuna.com/.
"""
from __future__ import annotations

import requests
from django.conf import settings

from .base import ExternalJob

_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


class AdzunaIntegration:
    source_name = "adzuna"

    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        if not (self.app_id and self.app_key):
            raise RuntimeError(
                "ADZUNA_APP_ID / ADZUNA_APP_KEY are not set. Get free "
                "credentials at https://developer.adzuna.com/ and add them "
                "to your .env."
            )

        url = _BASE_URL.format(country=country_code.lower())
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": " ".join(keywords),
            "results_per_page": 50,
            "content-type": "application/json",
        }
        if location and location.lower() != "remote":
            params["where"] = location
        if job_type == "fulltime":
            params["full_time"] = 1
        elif job_type == "parttime":
            params["part_time"] = 1
        elif job_type == "contract":
            params["contract"] = 1

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()

        jobs = []
        for item in payload.get("results", []):
            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            compensation = ""
            if salary_min and salary_max:
                compensation = f"{salary_min:.0f} - {salary_max:.0f}"
            elif salary_min:
                compensation = f"{salary_min:.0f}+"

            jobs.append(
                ExternalJob(
                    external_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    company=(item.get("company") or {}).get("display_name", ""),
                    location=(item.get("location") or {}).get("display_name", ""),
                    description=item.get("description", ""),
                    url=item.get("redirect_url", ""),
                    compensation_raw=compensation,
                )
            )
        return jobs
