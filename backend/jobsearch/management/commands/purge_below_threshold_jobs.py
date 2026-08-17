"""One-off cleanup for jobs saved before the salary threshold became
mandatory at search time (see jobsearch/services.py: save_results now skips
saving a job at all once a rule applies to it and it doesn't clear it,
counting missing/unparseable salary as 0). This retroactively removes
already-saved jobs that would now be skipped, so existing search results
match the new, stricter rule.

Only deletes jobs where a rule actually applies (a matching going-rate row,
or the profile's flat minimum) and the job fails it. Jobs with no
applicable rule yet (threshold_pass was already None/unevaluated, or no
rule matches this title) are left alone - same as new searches.

Usage:
    python manage.py purge_below_threshold_jobs --dry-run   # see what would go
    python manage.py purge_below_threshold_jobs             # actually delete
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from jobsearch.models import Job
from jobsearch.services import compute_threshold


class Command(BaseCommand):
    help = "Delete existing jobs that fail their profile's salary threshold (missing salary counts as 0)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be deleted without actually deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        candidates = Job.objects.filter(profile__isnull=False).select_related("profile")

        to_delete = []
        for job in candidates:
            if compute_threshold(job.profile, job.title, job.compensation_raw) is False:
                to_delete.append(job)

        if dry_run:
            self.stdout.write(f"Would delete {len(to_delete)} job(s):")
            for job in to_delete:
                self.stdout.write(
                    f"  - {job.title} @ {job.company} ({job.compensation_raw or 'no salary listed'})"
                )
            return

        count = len(to_delete)
        for job in to_delete:
            job.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} job(s) below their profile's salary threshold."))
