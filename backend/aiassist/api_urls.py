from django.urls import path

from . import api_views

app_name = "aiassist_api"

urlpatterns = [
    path("jobs/<int:job_id>/tailor-cv/", api_views.tailor_cv, name="tailor_cv"),
    path("jobs/<int:job_id>/cover-letter/", api_views.cover_letter, name="cover_letter"),
    path("jobs/<int:job_id>/qa/", api_views.qa, name="qa"),
    path("jobs/<int:job_id>/drafts/", api_views.drafts, name="drafts"),
]
