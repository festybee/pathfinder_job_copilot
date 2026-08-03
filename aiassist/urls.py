from django.urls import path

from . import views

app_name = "aiassist"

urlpatterns = [
    path("jobs/<int:job_id>/tailor-cv/", views.tailor_cv, name="tailor_cv"),
    path("jobs/<int:job_id>/cover-letter/", views.cover_letter, name="cover_letter"),
    path("jobs/<int:job_id>/qa/", views.qa, name="qa"),
]
