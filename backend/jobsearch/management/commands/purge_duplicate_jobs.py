"""One-off cleanup for duplicate job postings already in the tracker - the
same job reposted under a different external_id (common with recruiters on
Reed/Indeed) previously created a separate Job row each time, since
uniqueness was only enforced on (owner, source, external_id). Search now
also dedupes by (title, company, location) at save time - see
jobsearch/services.py - this catches up jobs saved before that existed.

Keeps the oldest (first-saved) row per (owner, title, company, location)
group and deletes the rest, regardless of source.

Usage:
    python manage.py purge_duplicate_jobs --dry-run   # see what would go
    python manage.py purge_duplicate_jobs             # actually delete
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand

from jobsearch.models import Job


class Command(BaseCommand):
    help = "Delete duplicate job postings (same title/company/location for the same owner), keeping the oldest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be deleted without actually deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        groups: dict[tuple, list[Job]] = defaultdict(list)

        for job in Job.objects.all().order_by("created_at"):
            key = (
                job.owner_id,
                job.title.strip().lower(),
                job.company.strip().lower(),
                job.location.strip().lower(),
            )
            groups[key].append(job)

        to_delete = []
        for jobs in groups.values():
            if len(jobs) > 1:
                to_delete.extend(jobs[1:])  # keep the oldest, drop the rest

        if dry_run:
            self.stdout.write(f"Would delete {len(to_delete)} duplicate job(s):")
            for job in to_delete:
                self.stdout.write(f"  - {job.title} @ {job.company} ({job.location})")
            return

        count = len(to_delete)
        for job in to_delete:
            job.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} duplicate job(s)."))
