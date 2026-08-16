"""
Django settings for Pathfinder Job Copilot.

API-only backend (django rest framework, under /api/) consumed by the
React app in frontend/, which is the single UI. The API uses token auth
(Authorization: Token <key>) rather than session cookies, since the
frontend runs on a different origin/deployment entirely (Vercel vs.
Railway) - avoids CORS+CSRF-cookie complexity. django.contrib.admin is
still mounted at /admin/ for superuser/user-approval management.
"""
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "accounts",
    "portfolio",
    "jobsearch",
    "aiassist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        # No project-level template dir - the only Django-rendered pages
        # left are django.contrib.admin's own, which come from APP_DIRS.
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Defaults to local sqlite so the project runs with zero setup; set
# DATABASE_URL (e.g. postgres://user:pass@host:5432/dbname) for Postgres.
# Read manually rather than via dj_database_url.config(default=...): if
# DATABASE_URL is present in .env but blank, os.environ still has the key
# set to "", which overrides the default and produces an empty (dummy)
# backend - so treat a blank value as "not set" ourselves.
_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# STATICFILES_DIRS deliberately not set - no custom static/ dir anymore
# (that was only for the removed template UI). STATIC_URL/ROOT stay since
# django.contrib.admin needs them for its own CSS/JS via collectstatic.
# WhiteNoise (see MIDDLEWARE) serves STATIC_ROOT directly from the Django
# process in production - no separate static host/CDN needed for /admin/.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# LOGIN_URL/LOGIN_REDIRECT_URL/LOGOUT_REDIRECT_URL deliberately not set -
# those pointed at the removed template UI's own login page. The API
# doesn't redirect on auth failure, it just returns 401/403 JSON.

# New signups are created with is_active=False (see accounts.forms and
# accounts.serializers) and need an admin to flip them to active in
# /admin/ before they can log in. AllowAllUsersModelBackend (unlike the
# default ModelBackend) still lets authenticate() succeed for inactive
# users instead of silently returning None, so both login views below can
# tell "wrong password" apart from "pending approval" and say so.
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.AllowAllUsersModelBackend"]

# --- Third-party API keys (all optional at import time, checked when used) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
REED_API_KEY = os.environ.get("REED_API_KEY")
JSEARCH_API_KEY = os.environ.get("JSEARCH_API_KEY")

# --- REST API (for the React frontend in frontend/) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Vite's default dev server port, plus whatever production frontend
# origin(s) are set via env (e.g. https://job.pathwrightltd.com).
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

# Railway (and most PaaS hosts) terminate TLS at a proxy in front of the
# app, then forward plain HTTP internally with this header set - without
# it, Django thinks every request is insecure, which breaks CSRF checks
# on /admin/ (session/cookie-based, unlike the token-authenticated API).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Needed for /admin/'s login form (uses session + CSRF cookies) to work
# once it's served from a real domain rather than localhost. Set this via
# env in production, e.g. https://api.job.pathwrightltd.com - the token-
# authenticated API endpoints under /api/ aren't affected either way.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]
