from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import PendingApprovalAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=PendingApprovalAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("approvals/", views.pending_approvals, name="pending_approvals"),
    path("approvals/<int:pk>/approve/", views.approve_user, name="approve_user"),
]
