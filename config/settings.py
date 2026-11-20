"""
Django 5 settings for Order-to-Audit System.
Configured for production-grade traceability, immutable ledger tracking, and GST reporting.
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project: BASE_DIR is the repository root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Core Security Settings - Strictly required from environment (no insecure defaults)
if "SECRET_KEY" not in os.environ:
    raise RuntimeError("SECRET_KEY environment variable is required.")
SECRET_KEY = os.environ["SECRET_KEY"]

# DEBUG defaults to False for production safety
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# HTTPS / SSL configuration
USE_HTTPS = os.environ.get("USE_HTTPS", "False").lower() in ("true", "1", "t")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,web,0.0.0.0").split(",")
    if host.strip()
]

# CSRF Trusted Origins for reverse proxies and HTTPS deployments
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Application Definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Model change auditing & versioning
    "simple_history",
    # Domain Applications
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

# Templates: Root-level templates/ directory
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# Database Configuration - Strictly required PostgreSQL / dj-database-url (fails loudly if missing)
if "DATABASE_URL" not in os.environ:
    raise RuntimeError("DATABASE_URL environment variable is required.")

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ["DATABASE_URL"],
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Authentication & Redirect URLs
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:role_redirect"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization & Regional Financial Calendar
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images, Fonts) and WhiteNoise Storage
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# SSL & Security Headers
if USE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Statutory GST & Benchmark Factory Settings
SELLER_NAME = os.environ.get("SELLER_NAME", "Kaveri Foods Mfg Ltd")
SELLER_GSTIN = os.environ.get("SELLER_GSTIN", "33AAAAA0000A1Z5")
SELLER_STATE_CODE = os.environ.get("SELLER_STATE_CODE", "33")  # Tamil Nadu

# Production Run Variance Engine Defaults (Strict Decimal - NO FLOATS)
DEFAULT_VARIANCE_TOLERANCE = Decimal(os.environ.get("DEFAULT_VARIANCE_TOLERANCE", "3.00"))
