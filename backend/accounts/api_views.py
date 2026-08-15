from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .serializers import SignupSerializer, UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    # No token issued - the account is inactive (see SignupSerializer.create)
    # until an admin approves it in /admin/, so there's nothing to log in
    # with yet. The frontend should show this message rather than treating
    # signup as an immediate login.
    return Response(
        {"detail": "Account created. An admin needs to approve it before you can log in."},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    # AUTHENTICATION_BACKENDS is set to AllowAllUsersModelBackend (see
    # settings.py), so authenticate() succeeds even for inactive users -
    # that's what lets us tell "wrong password" apart from "pending
    # approval" below, instead of both looking like invalid credentials.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response(
            {"detail": "Your account is pending admin approval."},
            status=status.HTTP_403_FORBIDDEN,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def pending_users(request):
    """IsAdminUser = request.user.is_staff, same requirement as the
    template-UI equivalent (accounts.views.pending_approvals)."""
    users = User.objects.filter(is_active=False).order_by("-date_joined")
    return Response(UserSerializer(users, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def approve_user(request, pk):
    target = get_object_or_404(User, pk=pk, is_active=False)
    target.is_active = True
    target.save(update_fields=["is_active"])
    return Response(UserSerializer(target).data)
