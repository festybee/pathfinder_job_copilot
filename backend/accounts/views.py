from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("jobsearch:job_list")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            # Not logging the new user in - accounts start inactive and
            # need admin approval first (see SignupForm.save()).
            messages.success(
                request,
                "Account created. An admin needs to approve it before you can log in - "
                "check back once you've been notified, then log in below.",
            )
            return redirect("accounts:login")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


def _require_staff(request):
    if not request.user.is_staff:
        raise PermissionDenied("Staff access required.")


@login_required
def pending_approvals(request):
    """In-app equivalent of filtering /admin/ Users by "Active: No" - a
    dedicated, discoverable page for the one task admins actually need to
    do often (approve new signups), linked from the main nav for staff."""
    _require_staff(request)
    pending_users = User.objects.filter(is_active=False).order_by("-date_joined")
    return render(request, "accounts/pending_approvals.html", {"pending_users": pending_users})


@login_required
def approve_user(request, pk):
    _require_staff(request)
    target = get_object_or_404(User, pk=pk, is_active=False)

    if request.method == "POST":
        target.is_active = True
        target.save(update_fields=["is_active"])
        messages.success(request, f"Approved '{target.username}'.")

    return redirect("accounts:pending_approvals")
