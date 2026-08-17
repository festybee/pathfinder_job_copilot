"""Common shape every job source integration returns, so the rest of the
app (views, matching, tracker) doesn't care whether a result came from
Adzuna, Reed, or something added later."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Protocol

import requests


def raise_clean_request_error(exc: requests.exceptions.RequestException) -> NoReturn:
    """Re-raise a requests exception as a short, plain-English RuntimeError.

    Never lets the raw exception (and thus the full request URL, and for
    sources that pass credentials as query params rather than headers,
    those credentials too) reach a warning shown in the UI. Caller's
    run_search() already prefixes the source name, so this only describes
    the failure itself.
    """
    if isinstance(exc, requests.exceptions.Timeout):
        raise RuntimeError("took too long to respond and was skipped.") from exc
    status = getattr(exc.response, "status_code", None)
    reason = getattr(exc.response, "reason", None)
    detail = f" ({status} {reason})" if status else ""
    raise RuntimeError(f"request failed{detail}.") from exc


@dataclass
class ExternalJob:
    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    compensation_raw: str = ""


class JobIntegration(Protocol):
    source_name: str

    def search(
        self, keywords: list[str], location: str, country_code: str, job_type: str = ""
    ) -> list[ExternalJob]:
        ...
