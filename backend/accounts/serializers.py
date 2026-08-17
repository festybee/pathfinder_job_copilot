from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff", "is_active", "date_joined"]


class SignupSerializer(serializers.ModelSerializer):
    # max_length is defensive, not a real-world constraint - avoids relying
    # on assumptions about how the password hasher behaves on an extremely
    # long input. username/email are already bounded by User's own field
    # definitions (max_length=150 / 254), enforced automatically since this
    # is a ModelSerializer.
    password = serializers.CharField(write_only=True, max_length=128, validators=[validate_password])

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        # is_active=False - accounts need admin approval (flip "Active" on
        # in /admin/) before they can log in. See api_views.login for how
        # that's surfaced back to the caller.
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )
