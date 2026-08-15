from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import EmailField


class SignupForm(UserCreationForm):
    email = EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # New accounts start inactive and need an admin to approve them
        # (flip "Active" on in /admin/) before they can log in.
        user.is_active = False
        if commit:
            user.save()
        return user


class PendingApprovalAuthenticationForm(AuthenticationForm):
    """Same as Django's default login form, except it tells a user with
    correct credentials but an inactive account WHY they can't log in,
    rather than the generic "invalid login" message. Only works together
    with AUTHENTICATION_BACKENDS = [AllowAllUsersModelBackend] in
    settings.py - the default ModelBackend rejects inactive users inside
    authenticate() itself, before this ever runs."""

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Your account is pending admin approval. You'll be able to log in once it's approved.",
                code="inactive",
            )
