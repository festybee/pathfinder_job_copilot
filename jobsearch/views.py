from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CriteriaProfileForm, JobStatusForm, ThresholdRowForm
from .models import CriteriaProfile, Job
from .services import run_search, save_results


@login_required
def criteria_list(request):
    if request.method == "POST":
        form = CriteriaProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.owner = request.user
            profile.save()
            return redirect("jobsearch:criteria_detail", pk=profile.pk)
    else:
        form = CriteriaProfileForm()

    profiles = CriteriaProfile.objects.filter(owner=request.user)
    return render(request, "jobsearch/criteria_list.html", {"profiles": profiles, "form": form})


@login_required
def criteria_edit(request, pk):
    profile = get_object_or_404(CriteriaProfile, pk=pk, owner=request.user)

    if request.method == "POST":
        form = CriteriaProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated '{profile.name}'.")
            return redirect("jobsearch:criteria_detail", pk=profile.pk)
    else:
        form = CriteriaProfileForm(instance=profile)

    return render(request, "jobsearch/criteria_edit.html", {"profile": profile, "form": form})


@login_required
def criteria_delete(request, pk):
    profile = get_object_or_404(CriteriaProfile, pk=pk, owner=request.user)

    if request.method == "POST":
        name = profile.name
        profile.delete()
        messages.success(request, f"Deleted '{name}'.")
        return redirect("jobsearch:criteria_list")

    return render(request, "jobsearch/criteria_delete_confirm.html", {"profile": profile})


@login_required
def criteria_detail(request, pk):
    profile = get_object_or_404(CriteriaProfile, pk=pk, owner=request.user)

    if request.method == "POST":
        row_form = ThresholdRowForm(request.POST)
        if row_form.is_valid():
            row = row_form.save(commit=False)
            row.profile = profile
            row.save()
            row_form = ThresholdRowForm()
    else:
        row_form = ThresholdRowForm()

    context = {
        "profile": profile,
        "threshold_rows": profile.threshold_rows.all(),
        "row_form": row_form,
    }

    if request.htmx:
        return render(request, "jobsearch/_threshold_rows.html", context)

    return render(request, "jobsearch/criteria_detail.html", context)


@login_required
def run_search_view(request, pk):
    profile = get_object_or_404(CriteriaProfile, pk=pk, owner=request.user)

    if request.method == "POST":
        results_by_source, warnings = run_search(profile)
        total_new = 0
        for source_key, external_jobs in results_by_source.items():
            total_new += save_results(profile, source_key, external_jobs)

        messages.success(request, f"Search complete: {total_new} new job(s) added to your tracker.")
        for warning in warnings:
            messages.warning(request, f"Source skipped - {warning}")

    return redirect("jobsearch:job_list")


JOBS_PER_PAGE = 20


@login_required
def job_list(request):
    status_filter = request.GET.get("status", "")
    sponsor_filter = request.GET.get("sponsor_status", "")
    jobs = Job.objects.filter(owner=request.user)
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if sponsor_filter:
        jobs = jobs.filter(sponsor_status=sponsor_filter)

    paginator = Paginator(jobs, JOBS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "jobs": page_obj,
        "page_obj": page_obj,
        "status_choices": Job.Status.choices,
        "sponsor_choices": Job.SponsorStatus.choices,
        "status_filter": status_filter,
        "sponsor_filter": sponsor_filter,
    }
    return render(request, "jobsearch/job_list.html", context)


@login_required
def job_update_status(request, pk):
    job = get_object_or_404(Job, pk=pk, owner=request.user)

    if request.method == "POST":
        form = JobStatusForm(request.POST, instance=job)
        if form.is_valid():
            form.save()

    context = {
        "job": job,
        "status_choices": Job.Status.choices,
        "sponsor_choices": Job.SponsorStatus.choices,
    }

    if request.htmx:
        return render(request, "jobsearch/_job_card.html", context)

    return redirect("jobsearch:job_list")
