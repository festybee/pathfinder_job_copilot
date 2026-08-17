from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import CriteriaProfile, Job, ThresholdRow
from .serializers import CriteriaProfileSerializer, JobSerializer, ThresholdRowSerializer
from .services import run_search, save_results


@api_view(["GET"])
def choices(request):
    """Enum choices the frontend needs for dropdowns, kept in one place
    (the models) rather than duplicated in the React code."""
    return Response(
        {
            "job_status": dict(Job.Status.choices),
            "sponsor_status": dict(Job.SponsorStatus.choices),
            "job_source": dict(Job.Source.choices),
            "job_type": dict(CriteriaProfile.JobType.choices),
            "salary_mode": dict(CriteriaProfile.SalaryMode.choices),
        }
    )


class CriteriaProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CriteriaProfileSerializer

    def get_queryset(self):
        return CriteriaProfile.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def search(self, request, pk=None):
        """POST /api/jobsearch/criteria/<id>/search/ - run a live search
        and save new results. Mirrors jobsearch.views.run_search_view."""
        profile = self.get_object()

        results_by_source, warnings = run_search(profile)
        total_new = 0
        total_skipped = 0
        for source_key, external_jobs in results_by_source.items():
            created, skipped = save_results(profile, source_key, external_jobs)
            total_new += created
            total_skipped += skipped

        return Response(
            {"new_jobs": total_new, "skipped_below_threshold": total_skipped, "warnings": warnings}
        )


class ThresholdRowViewSet(viewsets.ModelViewSet):
    serializer_class = ThresholdRowSerializer

    def get_queryset(self):
        qs = ThresholdRow.objects.filter(profile__owner=self.request.user)
        profile_id = self.request.query_params.get("profile")
        if profile_id:
            qs = qs.filter(profile_id=profile_id)
        return qs


class JobViewSet(viewsets.ModelViewSet):
    """Read + status/sponsor_status updates. No create/delete via the API -
    jobs only come from a search or (in the template UI) manual add."""

    serializer_class = JobSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = Job.objects.filter(owner=self.request.user)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        sponsor_filter = self.request.query_params.get("sponsor_status")
        if sponsor_filter:
            qs = qs.filter(sponsor_status=sponsor_filter)

        profile_filter = self.request.query_params.get("profile")
        if profile_filter:
            if profile_filter == "none":
                qs = qs.filter(profile__isnull=True)
            else:
                qs = qs.filter(profile_id=profile_filter)

        return qs
