from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("ai/", include("aiassist.urls")),
    path("", include("jobsearch.urls")),  # jobsearch:job_list serves "/"
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
