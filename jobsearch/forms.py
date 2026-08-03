from django import forms

from .models import CriteriaProfile, Job, ThresholdRow


class CriteriaProfileForm(forms.ModelForm):
    class Meta:
        model = CriteriaProfile
        fields = [
            "name",
            "keywords",
            "location",
            "country_code",
            "job_type",
            "salary_mode",
            "flat_minimum_salary",
        ]


class ThresholdRowForm(forms.ModelForm):
    class Meta:
        model = ThresholdRow
        fields = ["keyword_match", "occupation_code", "threshold_amount", "currency", "verified", "source_note"]


class JobStatusForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["status", "sponsor_status"]
