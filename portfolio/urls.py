from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("<int:pk>/delete/", views.document_delete, name="document_delete"),
]
