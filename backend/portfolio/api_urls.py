from rest_framework.routers import DefaultRouter

from .api_views import DocumentViewSet

app_name = "portfolio_api"

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
