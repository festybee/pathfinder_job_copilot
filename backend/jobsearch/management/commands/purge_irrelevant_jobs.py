"""One-off cleanup for jobs saved before search results were filtered for
title relevance (see jobsearch/services.py: run_search now requires a job's
title to actually contain one of the profile's search keywords, since Reed
in particular does loose/fuzzy server-side matching). Removes already-saved
jobs, linked to a profile, whose title doesn't contain any of that
profile's keywords - e.g. a "Trainee IT Support Assistant" posting that
slipped through a "data analyst" search.

Usage:
    python manage.py purge_irrelevant_jobs --dry-run   # see what would go
    python manage.py purge_irrelevant_jobs             # actually delete
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from jobsearch.models import Job


class Command(BaseCommand):
    help = "Delete existing jobs whose title doesn't contain any of their profile's search keywords."

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
            keywords = job.profile.keyword_list()
            if not keywords:
                continue
            title_lower = job.title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                to_delete.append(job)

        if dry_run:
            self.stdout.write(f"Would delete {len(to_delete)} job(s):")
            for job in to_delete:
                self.stdout.write(f"  - {job.title} @ {job.company} (profile: {job.profile.name})")
            return

        count = len(to_delete)
        for job in to_delete:
            job.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} job(s) not matching their profile's keywords."))
