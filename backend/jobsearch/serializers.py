from rest_framework import serializers

from .models import CriteriaProfile, Job, ThresholdRow


class ThresholdRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdRow
        fields = [
            "id",
            "profile",
            "keyword_match",
            "occupation_code",
            "threshold_amount",
            "currency",
            "verified",
            "source_note",
        ]

    def validate_profile(self, profile):
        request = self.context["request"]
        if profile.owner_id != request.user.id:
            raise serializers.ValidationError("Not your criteria profile.")
        return profile


class CriteriaProfileSerializer(serializers.ModelSerializer):
    # Each keyword is a separate request to every job source (see
    # jobsearch/services.py:run_search) - a profile with too many turns a
    # search into dozens of sequential/concurrent external calls, which is
    # what caused a Gunicorn worker timeout with a 9-keyword profile before
    # that was parallelized. Enforced here (not just recommended in the
    # frontend guide) so it can't be bypassed by calling the API directly.
    MAX_KEYWORDS = 12

    threshold_rows = ThresholdRowSerializer(many=True, read_only=True)

    class Meta:
        model = CriteriaProfile
        fields = [
            "id",
            "name",
            "keywords",
            "location",
            "country_code",
            "job_type",
            "salary_mode",
            "flat_minimum_salary",
            "include_sponsorship_keyword",
            "is_active",
            "created_at",
            "threshold_rows",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_keywords(self, value):
        count = len([k for k in value.split(",") if k.strip()])
        if count > self.MAX_KEYWORDS:
            raise serializers.ValidationError(
                f"Too many keywords ({count}) - max {self.MAX_KEYWORDS} per profile. Split extra role "
                "variants into a separate criteria profile instead."
            )
        return value


class JobSerializer(serializers.ModelSerializer):
    profile_name = serializers.CharField(source="profile.name", read_only=True, default=None)

    class Meta:
        model = Job
        fields = [
            "id",
            "profile",
            "profile_name",
            "source",
            "external_id",
            "title",
            "company",
            "location",
            "description",
            "compensation_raw",
            "url",
            "status",
            "sponsor_status",
            "threshold_pass",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "profile",
            "profile_name",
            "source",
            "external_id",
            "title",
            "company",
            "location",
            "description",
            "compensation_raw",
            "url",
            "threshold_pass",
            "created_at",
            "updated_at",
        ]
        # Only status and sponsor_status are writable via the API - everything
        # else about a job comes from the search source, not user edits.
