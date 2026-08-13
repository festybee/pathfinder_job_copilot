from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api_views

app_name = "jobsearch_api"

router = DefaultRouter()
router.register("criteria", api_views.CriteriaProfileViewSet, basename="criteria-profile")
router.register("threshold-rows", api_views.ThresholdRowViewSet, basename="threshold-row")
router.register("jobs", api_views.JobViewSet, basename="job")

urlpatterns = [
    path("choices/", api_views.choices, name="choices"),
] + router.urls
