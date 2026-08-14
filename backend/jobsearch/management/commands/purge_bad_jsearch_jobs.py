"""One-off cleanup for jobs pulled in by the JSearch integration before its
country filtering was fixed (see jobsearch/integrations/jsearch.py) - the
API's own "country" request param isn't reliably honored, so earlier
searches could save postings from the wrong country entirely (e.g. US
postings showing up for a GB-scoped criteria profile).

Only touches Job rows with source=jsearch that are linked to a profile;
manually-added jobs or jobs from other sources are left untouched. Jobs
with a blank location, or a profile country_code this app doesn't have a
name-variant mapping for, are left as-is rather than guessed-and-deleted -
better to leave a few stragglers than risk deleting something legitimate.

Usage:
    python manage.py purge_bad_jsearch_jobs --dry-run   # see what would go
    python manage.py purge_bad_jsearch_jobs             # actually delete
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from jobsearch.integrations.jsearch import _COUNTRY_NAME_VARIANTS
from jobsearch.models import Job


class Command(BaseCommand):
    help = "Delete existing JSearch-sourced jobs whose location doesn't match their profile's country."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be deleted without actually deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        candidates = Job.objects.filter(source=Job.Source.JSEARCH, profile__isnull=False).select_related(
            "profile"
        )

        to_delete = []
        skipped_no_mapping = 0
        for job in candidates:
            expected = _COUNTRY_NAME_VARIANTS.get(job.profile.country_code.upper())
            if not expected:
                skipped_no_mapping += 1
                continue
            if not job.location:
                continue
            location_lower = job.location.lower()
            if not any(name in location_lower for name in expected):
                to_delete.append(job)

        if dry_run:
            self.stdout.write(f"Would delete {len(to_delete)} job(s):")
            for job in to_delete:
                self.stdout.write(f"  - {job.title} @ {job.company} ({job.location})")
            if skipped_no_mapping:
                self.stdout.write(
                    f"({skipped_no_mapping} job(s) skipped - profile country_code not in the name-variant map)"
                )
            return

        count = len(to_delete)
        for job in to_delete:
            job.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} mismatched-country JSearch job(s)."))
