"""
Root URL configuration.

Routes both UIs against the same views/data: server-rendered template
views (accounts/, portfolio/, ai/, and the root for jobsearch), and the
REST API consumed by the React frontend, all under /api/.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Template UI
    path("accounts/", include("accounts.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("ai/", include("aiassist.urls")),
    path("", include("jobsearch.urls")),
    # REST API (for the React frontend)
    path("api/auth/", include("accounts.api_urls")),
    path("api/portfolio/", include("portfolio.api_urls")),
    path("api/jobsearch/", include("jobsearch.api_urls")),
    path("api/aiassist/", include("aiassist.api_urls")),
]
