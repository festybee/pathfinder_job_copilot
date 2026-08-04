"""Download and load the UK government's register of licensed Worker/
Temporary Worker sponsors into SponsorRegisterEntry.

The register is published as a dated CSV (a new file roughly monthly), so
we don't hardcode the filename - we fetch the publication page first and
pull out whichever CSV link is currently live, then download that.

Usage:
    python manage.py sync_sponsor_register
    python manage.py sync_sponsor_register --url https://.../some-file.csv
"""
from __future__ import annotations

import csv
import io
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jobsearch.models import SponsorRegisterEntry
from jobsearch.sponsor_register import normalize_company_name

_PUBLICATION_PAGE = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
_CSV_LINK_RE = re.compile(
    r'https://assets\.publishing\.service\.gov\.uk/media/[^"\'\s]+?Worker[^"\'\s]*?\.csv',
    re.IGNORECASE,
)
_BATCH_SIZE = 5000


class Command(BaseCommand):
    help = "Download and load the UK register of licensed Worker/Temporary Worker sponsors."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            help="Skip auto-discovery and download this CSV URL directly.",
        )

    def handle(self, *args, **options):
        csv_url = options.get("url") or self._discover_csv_url()
        self.stdout.write(f"Downloading {csv_url} ...")

        response = requests.get(csv_url, timeout=120)
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")

        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
        self.stdout.write(f"Columns: {fieldnames}")

        entries = []
        for row in reader:
            org_name = (row.get("Organisation Name") or "").strip()
            if not org_name:
                continue
            entries.append(
                SponsorRegisterEntry(
                    organisation_name=org_name,
                    organisation_name_normalized=normalize_company_name(org_name),
                    town_city=(row.get("Town/City") or "").strip(),
                    county=(row.get("County") or "").strip(),
                    rating=(row.get("Type & Rating") or "").strip(),
                    route=(row.get("Route") or "").strip(),
                )
            )

        if not entries:
            raise CommandError(
                "Parsed 0 rows from the CSV - the register's column layout may "
                "have changed. Check the file manually before retrying."
            )

        with transaction.atomic():
            SponsorRegisterEntry.objects.all().delete()
            for i in range(0, len(entries), _BATCH_SIZE):
                SponsorRegisterEntry.objects.bulk_create(entries[i : i + _BATCH_SIZE])

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(entries)} sponsor register entries."))
        self.stdout.write(
            "Run 'python manage.py check_sponsors' to re-check existing jobs against the updated register."
        )

    def _discover_csv_url(self) -> str:
        response = requests.get(_PUBLICATION_PAGE, timeout=30)
        response.raise_for_status()
        match = _CSV_LINK_RE.search(response.text)
        if not match:
            raise CommandError(
                f"Couldn't find a CSV link on {_PUBLICATION_PAGE}. The page layout "
                "may have changed - pass --url with the direct CSV link instead "
                "(find it manually on that page)."
            )
        return match.group(0)
