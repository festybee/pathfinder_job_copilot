"""Common shape every job source integration returns, so the rest of the
app (views, matching, tracker) doesn't care whether a result came from
Adzuna, Reed, or something added later."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
