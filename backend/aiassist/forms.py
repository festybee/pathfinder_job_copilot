from django import forms

from portfolio.models import Document


class DocumentSelectForm(forms.Form):
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Tick which portfolio documents the draft should be grounded in.",
    )

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["documents"].queryset = Document.objects.filter(owner=owner)


class QuestionForm(DocumentSelectForm):
    question = forms.CharField(widget=forms.Textarea, label="Application question")
