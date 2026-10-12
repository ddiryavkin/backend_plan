import os
from pathlib import Path

import structlog
from dotenv import load_dotenv

from backend.middleware import add_user_id

BASE_DIR = Path(__file__).resolve().parent.parent

# Локальный .env (если есть). Уже заданные переменные окружения не перезаписываются,
# поэтому значения из docker-compose имеют приоритет.
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "plan",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backend.middleware.RequestContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "backend.urls"
WSGI_APPLICATION = "backend.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "NAME": os.environ.get("POSTGRES_DB", "plan"),
        "USER": os.environ.get("POSTGRES_USER", "plan"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "plan"),
    }
}

# ClickHouse
CLICKHOUSE = {
    "HOST": os.environ.get("CLICKHOUSE_HOST", "localhost"),
    "PORT": int(os.environ.get("CLICKHOUSE_PORT", "8123")),
    "DATABASE": os.environ.get("CLICKHOUSE_DB", "plan"),
    "USER": os.environ.get("CLICKHOUSE_USER", "plan"),
    "PASSWORD": os.environ.get("CLICKHOUSE_PASSWORD", "plan"),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Plan API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
}

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# В DEBUG статика раздаётся из приложений без collectstatic
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Логи
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_JSON = os.environ.get("LOG_JSON", "0") == "1"

_shared_processors = [
    structlog.contextvars.merge_contextvars,
    add_user_id,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]
_renderers = (
    [structlog.processors.format_exc_info, structlog.processors.JSONRenderer(ensure_ascii=False)]
    if LOG_JSON
    else [structlog.dev.ConsoleRenderer()]
)

structlog.configure(
    processors=[*_shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": _shared_processors,
            "processors": [structlog.stdlib.ProcessorFormatter.remove_processors_meta, *_renderers],
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "structlog"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # Убираем стандартные обработчики Django, чтобы не было дублей: всё идёт через root
        "django": {"handlers": [], "propagate": True},
        # Каждый запрос уже логирует RequestContextMiddleware
        "django.server": {"handlers": [], "level": "WARNING", "propagate": True},
    },
}
