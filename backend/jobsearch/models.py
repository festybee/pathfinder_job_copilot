from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

# Sanity bound, not a real-world limit - guards against a fat-fingered extra
# zero (e.g. 4,170,000 instead of 41,700) silently producing a threshold no
# job could ever clear, rather than an obviously-wrong value the user would
# notice and fix. PositiveIntegerField already rejects negative numbers.
_MAX_SALARY = 1_000_000


class CriteriaProfile(models.Model):
    """A saved, editable search criteria set. Deliberately not hardcoded to
    any single job title/country - a user can have several of these."""

    class SalaryMode(models.TextChoices):
        GOING_RATE = "going_rate", "Occupation going-rate table"
        FLAT_MINIMUM = "flat_minimum", "Flat minimum salary"

    class JobType(models.TextChoices):
        ANY = "", "Any"
        FULLTIME = "fulltime", "Full-time"
        PARTTIME = "parttime", "Part-time"
        CONTRACT = "contract", "Contract"
        TEMPORARY = "temporary", "Temporary"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="criteria_profiles"
    )
    name = models.CharField(max_length=100, help_text="e.g. 'UK Data/BI roles'")
    keywords = models.CharField(
        max_length=300, help_text="Comma-separated job titles/keywords, e.g. 'data analyst, business analyst'"
    )
    location = models.CharField(max_length=150, blank=True, help_text="City, or 'remote'")
    country_code = models.CharField(max_length=2, default="GB")
    job_type = models.CharField(max_length=20, choices=JobType.choices, blank=True)
    salary_mode = models.CharField(
        max_length=20, choices=SalaryMode.choices, default=SalaryMode.GOING_RATE
    )
    flat_minimum_salary = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(_MAX_SALARY)],
        help_text="Only used when salary_mode = flat_minimum",
    )
    include_sponsorship_keyword = models.BooleanField(
        default=False,
        help_text=(
            "Also search 'visa sponsorship' as an extra term, to surface postings "
            "that explicitly mention it. Weak signal - most sponsor-eligible jobs "
            "don't say so in the text. See the going-rate table and sponsor-status "
            "column for the more reliable checks."
        ),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def keyword_list(self) -> list[str]:
        return [k.strip() for k in self.keywords.split(",") if k.strip()]


class ThresholdRow(models.Model):
    """One row of an occupation going-rate table, scoped to a CriteriaProfile.

    Generalized so it works for any country's system: UK SOC codes, US
    prevailing wage, Canada NOC, Australia ANZSCO, etc. - the user edits
    the rows; nothing here is UK-specific.
    """

    profile = models.ForeignKey(
        CriteriaProfile, on_delete=models.CASCADE, related_name="threshold_rows"
    )
    keyword_match = models.CharField(
        max_length=150, help_text="Job title/keyword this row applies to, e.g. 'data analyst'"
    )
    occupation_code = models.CharField(max_length=50, blank=True, help_text="e.g. SOC 3544")
    threshold_amount = models.PositiveIntegerField(validators=[MaxValueValidator(_MAX_SALARY)])
    currency = models.CharField(max_length=3, default="GBP")
    verified = models.BooleanField(
        default=False, help_text="Whether this figure has been checked against an official source"
    )
    source_note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["keyword_match"]

    def __str__(self):
        return f"{self.keyword_match}: {self.threshold_amount} {self.currency}"


class Job(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        INTERESTED = "interested", "Interested"
        TAILORING = "tailoring", "Tailoring"
        APPLIED = "applied", "Applied"
        INTERVIEWING = "interviewing", "Interviewing"
        OFFER = "offer", "Offer"
        REJECTED = "rejected", "Rejected"

    class SponsorStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        LIKELY = "likely", "Likely"
        CONFIRMED = "confirmed", "Confirmed"
        NO = "no", "No"

    class Source(models.TextChoices):
        ADZUNA = "adzuna", "Adzuna"
        REED = "reed", "Reed"
        JSEARCH = "jsearch", "JSearch"
        MANUAL = "manual", "Manually added"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs"
    )
    profile = models.ForeignKey(
        CriteriaProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs"
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    compensation_raw = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    sponsor_status = models.CharField(
        max_length=20, choices=SponsorStatus.choices, default=SponsorStatus.UNKNOWN
    )
    threshold_pass = models.BooleanField(
        null=True, blank=True, help_text="Whether compensation clears the matched threshold row"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "source", "external_id"],
                name="unique_job_per_owner_source",
                condition=~models.Q(external_id=""),
            )
        ]

    def __str__(self):
        return f"{self.title} @ {self.company}"


class SearchRun(models.Model):
    """A record of one 'Run search now' click - admin-only visibility into
    which sources are flaky/slow/rate-limited over time. The end user never
    sees this: they don't need to know Adzuna/Reed/JSearch exist as
    distinct systems, only that their tracker did or didn't get new jobs.

    profile is nullable + profile_name is a snapshot, so this stays
    readable in /admin/ even if the profile is later renamed or deleted
    (Job does the same thing via JobSerializer.profile_name).
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_runs"
    )
    profile = models.ForeignKey(
        CriteriaProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="search_runs"
    )
    profile_name = models.CharField(max_length=100)
    new_jobs = models.PositiveIntegerField(default=0)
    skipped_below_threshold = models.PositiveIntegerField(default=0)
    skipped_duplicate = models.PositiveIntegerField(default=0)
    warnings = models.TextField(
        blank=True, help_text="One per line - which source(s) had trouble and why, if any."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile_name} search by {self.owner} at {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def had_warnings(self) -> bool:
        return bool(self.warnings.strip())


class SponsorRegisterEntry(models.Model):
    """One row of the UK government's register of licensed Worker/Temporary
    Worker sponsors. Shared reference data, not scoped to a user - populated
    by `python manage.py sync_sponsor_register` and matched against by
    company name (see jobsearch.sponsor_register.check_sponsor_licence).

    Source: https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers
    UK-specific by nature - other countries would need an equivalent
    register and a separate model/command if this pattern gets reused.
    """

    organisation_name = models.CharField(max_length=300)
    organisation_name_normalized = models.CharField(max_length=300)
    town_city = models.CharField(max_length=150, blank=True)
    county = models.CharField(max_length=150, blank=True)
    rating = models.CharField(max_length=100, blank=True, help_text="'Type & Rating' column, e.g. 'Worker (A rating)'")
    route = models.CharField(max_length=150, blank=True, help_text="e.g. 'Skilled Worker'")
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["organisation_name_normalized"])]

    def __str__(self):
        return self.organisation_name
