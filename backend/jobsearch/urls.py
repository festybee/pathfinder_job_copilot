from django.urls import path

from . import views

app_name = "jobsearch"

urlpatterns = [
    path("", views.job_list, name="job_list"),
    path("jobs/<int:pk>/status/", views.job_update_status, name="job_update_status"),
    path("criteria/", views.criteria_list, name="criteria_list"),
    path("criteria/<int:pk>/", views.criteria_detail, name="criteria_detail"),
    path("criteria/<int:pk>/edit/", views.criteria_edit, name="criteria_edit"),
    path("criteria/<int:pk>/delete/", views.criteria_delete, name="criteria_delete"),
    path("criteria/<int:pk>/search/", views.run_search_view, name="run_search"),
]
