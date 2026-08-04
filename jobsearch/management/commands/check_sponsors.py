"""Re-check existing jobs' sponsor_status against the SponsorRegisterEntry
table (run sync_sponsor_register first). Only ever upgrades Unknown/Likely
jobs to Confirmed on a match - never touches jobs already Confirmed or a
manually-set No.

Usage:
    python manage.py check_sponsors
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from jobsearch.models import Job, SponsorRegisterEntry
from jobsearch.sponsor_register import apply_sponsor_check


class Command(BaseCommand):
    help = "Re-check existing jobs' sponsor_status against the sponsor register."

    def handle(self, *args, **options):
        if not SponsorRegisterEntry.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Sponsor register is empty - run 'python manage.py "
                    "sync_sponsor_register' first."
                )
            )
            return

        candidates = Job.objects.exclude(sponsor_status=Job.SponsorStatus.CONFIRMED).exclude(
            sponsor_status=Job.SponsorStatus.NO
        )
        updated = 0
        for job in candidates:
            if apply_sponsor_check(job):
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {candidates.count()} job(s), confirmed sponsorship for {updated}."
            )
        )
