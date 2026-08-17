"""Adzuna job search integration.

Adzuna has decent multi-country coverage and returns salary data on many
listings, which is what makes the going-rate/threshold check possible.
Free tier requires an app_id + app_key from https://developer.adzuna.com/.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

from .base import ExternalJob, raise_clean_request_error

_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

# Unlike Reed (basic auth) and JSearch (header), Adzuna takes app_id/app_key
# as URL query params - requests.Response/HTTPError.__str__ includes the
# full request URL, so letting one bubble up unmodified would leak
# credentials into warnings shown in the UI and into logs. Always catch and
# re-raise with a message that omits the URL.
_MAX_RETRIES = 3

# Adzuna's free tier has a burst/rate limit noticeably tighter than Reed's
# or JSearch's - running many keywords at high concurrency (as the other
# two sources safely do) trips 429s here. Keep this low and lean on retry
# instead.
_MAX_WORKERS = 2

# Adzuna normalizes salary_min/salary_max to an annualized full-time
# equivalent regardless of the posting's stated pay period, so (unlike
# Reed's search endpoint) these figures are safe to compare against an
# annual threshold. Currency depends on which country site is queried.
_CURRENCY_BY_COUNTRY = {
    "GB": "GBP",
    "US": "USD",
    "CA": "CAD",
    "AU": "AUD",
    "NZ": "NZD",
    "IE": "EUR",
    "DE": "EUR",
    "FR": "EUR",
    "NL": "EUR",
    "IN": "INR",
    "SG": "SGD",
}


class AdzunaIntegration:
    source_name = "adzuna"

    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY

    def _get_with_retry(self, url: str, params: dict) -> requests.Response:
        # Unlike Reed (basic auth) and JSearch (header), Adzuna's
        # app_id/app_key are sent as URL query params - an unmodified
        # requests exception would leak them into a warning shown in the
        # UI, so every path here goes through raise_clean_request_error.
        try:
            for attempt in range(_MAX_RETRIES):
                response = requests.get(url, params=params, timeout=15)
                if response.status_code != 429:
                    break
                time.sleep(2**attempt)  # 1s, 2s, 4s
            else:
                raise RuntimeError("rate limited (429) - too many requests, even after retrying.")

            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise_clean_request_error(exc)
        return response

    def _search_one(self, keyword: str, location: str, country_code: str, job_type: str) -> list[ExternalJob]:
        url = _BASE_URL.format(country=country_code.lower())
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": keyword,
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

        response = self._get_with_retry(url, params)
        payload = response.json()

        results = []
        for item in payload.get("results", []):
            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            currency = _CURRENCY_BY_COUNTRY.get(country_code.upper(), country_code.upper())
            compensation = ""
            if salary_min and salary_max:
                compensation = f"{currency} {salary_min:.0f} - {salary_max:.0f}"
            elif salary_min:
                compensation = f"{currency} {salary_min:.0f}+"

            results.append(
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
        return results

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        if not (self.app_id and self.app_key):
            raise RuntimeError(
                "ADZUNA_APP_ID / ADZUNA_APP_KEY are not set. Get free "
                "credentials at https://developer.adzuna.com/ and add them "
                "to your .env."
            )

        # Run one search per keyword phrase and merge results, rather than
        # joining all keywords into a single query - Adzuna's "what" param
        # requires every word in the query to be present, so "risk
        # assessment compliance enforcement" as one string demands all of
        # those words appear together and matches almost nothing. Run a few
        # concurrently (fewer than Reed/JSearch - see _MAX_WORKERS) so a
        # long keyword list doesn't take forever serially, without tripping
        # Adzuna's tighter rate limit.
        keyword_list = keywords or [""]
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(keyword_list))) as executor:
            batches = list(
                executor.map(lambda kw: self._search_one(kw, location, country_code, job_type), keyword_list)
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
