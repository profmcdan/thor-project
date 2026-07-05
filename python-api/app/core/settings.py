import os
import sys
from pathlib import Path
from datetime import timedelta
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environ
env = environ.Env(
    DEBUG=(bool, True),
)

# Read environment variables from .env in workspace root
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

SECRET_KEY = env.str('SECRET_KEY', 'django-insecure-od)6k8mssilrail=lib_zezb&o-i_qom($l6_3=ws1mx&p$mi3')

DEBUG = env.bool('DEBUG', True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party packages
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    
    # Local apps
    'user.apps.UserConfig',
    'wallet.apps.WalletConfig',
    'transaction.apps.TransactionConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'


# Database configuration (Postgres 18 by default)
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# Disable connection pooling during unit tests to prevent SQLite "database table is locked" conflicts
conn_max_age = 0 if 'test' in sys.argv else 600

# Route through PgBouncer connection pooler in transaction mode for normal operations.
# Django migrations (advisory locks) and unit tests require direct database connection.
is_migration = any(cmd in sys.argv for cmd in ['migrate', 'makemigrations'])
is_test = 'test' in sys.argv

pg_host = env.str('PGBOUNCER_HOST', '')
pg_port = env.str('PGBOUNCER_PORT', '')
use_pgbouncer = pg_host and pg_port and not is_migration and not is_test

if env.str('DATABASE_URL', default=''):
    DATABASES = {
        'default': env.db('DATABASE_URL')
    }
    DATABASES['default']['CONN_MAX_AGE'] = conn_max_age
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
else:
    postgres_password = env.str('MAIN_POSTGRES_PASSWORD', 'password')
    db_host = pg_host if use_pgbouncer else env.str('POSTGRES_HOST', 'db')
    db_port = pg_port if use_pgbouncer else env.str('POSTGRES_PORT', '5432')
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('POSTGRES_DB', 'wallet_db'),
            'USER': env.str('POSTGRES_USER', 'postgres'),
            'PASSWORD': postgres_password,
            'HOST': db_host,
            'PORT': db_port,
            'CONN_MAX_AGE': conn_max_age,
            'CONN_HEALTH_CHECKS': True,
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos' # Defaulting to Nigeria Lagos timezone as requested Naira base

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Custom User Model
AUTH_USER_MODEL = 'user.User'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Simple JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Redis Caching Backend (fallback to LocMemCache during testing)
if 'test' in sys.argv or not env.str('REDIS_URL', ''):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': env.str('REDIS_URL', 'redis://redis:6379/1'),
        }
    }

# Celery Configurations
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'audit-wallet-balances-every-hour': {
        'task': 'wallet.tasks.audit_wallet_balances',
        'schedule': 3600.0,  # runs hourly
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

SPECTACULAR_SETTINGS = {
    'TITLE': 'Thor Digital Wallet API',
    'DESCRIPTION': 'High-performance, concurrent digital wallet API system with ledger integrity.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
