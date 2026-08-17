from django.urls import path

from . import api_views

app_name = "accounts_api"

urlpatterns = [
    path("signup/", api_views.signup, name="signup"),
    path("login/", api_views.login, name="login"),
    path("logout/", api_views.logout, name="logout"),
    path("me/", api_views.me, name="me"),
    path("pending-users/", api_views.pending_users, name="pending_users"),
    path("pending-users/<int:pk>/approve/", api_views.approve_user, name="approve_user"),
    path("approved-users/", api_views.approved_users, name="approved_users"),
    path("approved-users/<int:pk>/suspend/", api_views.suspend_user, name="suspend_user"),
    path("approved-users/<int:pk>/", api_views.delete_user, name="delete_user"),
]
