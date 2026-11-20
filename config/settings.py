"""
Django 5 settings for Order-to-Audit System.
Configured for production-grade traceability, immutable ledger tracking, and GST reporting.
"""

from pathlib import Path
import os
import sys

# Build paths inside the project: BASE_DIR is the repository root
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps/ directory to Python path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Core Security Settings
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-snackfactory-dev-secret-key-replace-in-production-12345'
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,web,0.0.0.0').split(',')
    if host.strip()
]

# Application Definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Audit & History tracking (graceful import)
try:
    import simple_history
    INSTALLED_APPS.append('simple_history')
    HAS_SIMPLE_HISTORY = True
except ImportError:
    HAS_SIMPLE_HISTORY = False

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if HAS_SIMPLE_HISTORY:
    MIDDLEWARE.append('simple_history.middleware.HistoryRequestMiddleware')

ROOT_URLCONF = 'config.urls'

# Templates: Root-level templates/ directory
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration
# Uses PostgreSQL in Docker / production via DATABASE_URL; falls back to local SQLite3
database_url = os.environ.get('DATABASE_URL')
if database_url:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(
                default=database_url,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    except ImportError:
        # Fallback if dj-database-url is not yet installed in host environment
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization & Regional Financial Calendar
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images, Fonts)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Statutory GST & Benchmark Factory Settings
SELLER_NAME = os.environ.get('SELLER_NAME', 'Kaveri Foods Mfg Ltd')
SELLER_GSTIN = os.environ.get('SELLER_GSTIN', '33AAAAA0000A1Z5')
SELLER_STATE_CODE = os.environ.get('SELLER_STATE_CODE', '33')  # Tamil Nadu

# Production Run Variance Engine Defaults
DEFAULT_VARIANCE_TOLERANCE = float(os.environ.get('DEFAULT_VARIANCE_TOLERANCE', '3.0'))

# Precision Decimals Configuration (Money: 2, Quantities: 4)
DECIMAL_PLACES_MONEY = 2
DECIMAL_PLACES_QTY = 4
