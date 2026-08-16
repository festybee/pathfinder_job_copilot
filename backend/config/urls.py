"""
Root URL configuration.

Django is API-only - the React app in frontend/ is the single UI, talking
to everything under /api/. /admin/ is Django's own built-in admin panel,
kept for superuser/user-approval management and as a fallback.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.api_urls")),
    path("api/portfolio/", include("portfolio.api_urls")),
    path("api/jobsearch/", include("jobsearch.api_urls")),
    path("api/aiassist/", include("aiassist.api_urls")),
]
