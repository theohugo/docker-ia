"""Django settings for CadrIA.

The default configuration deliberately works without external services: SQLite
and the deterministic ``demo`` AI provider are used locally. Production values
are supplied through environment variables.
"""

import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    AI_TIMEOUT_SECONDS=(float, 30.0),
    AI_MAX_INPUT_CHARS=(int, 12_000),
    GROQ_TIMEOUT_SECONDS=(float, 60.0),
    OLLAMA_TIMEOUT_SECONDS=(float, 120.0),
    OLLAMA_NUM_CTX=(int, 4_096),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-cadria-local-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "briefs.apps.BriefsConfig",
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
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or "test" in sys.argv
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery / Redis
REDIS_URL = env("REDIS_URL", default="redis://cache:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

# AI provider. ``demo`` is deterministic and never reaches the network.
AI_PROVIDER = env("AI_PROVIDER", default="demo")
AI_API_KEY = env("AI_API_KEY", default="")
AI_BASE_URL = env("AI_BASE_URL", default="")
AI_MODEL = env("AI_MODEL", default="demo-cadria-v1")
AI_TIMEOUT_SECONDS = env("AI_TIMEOUT_SECONDS")
AI_MAX_INPUT_CHARS = env("AI_MAX_INPUT_CHARS")
AI_PROMPT_VERSION = env("AI_PROMPT_VERSION", default="v1")

# Secondary provider tried when the primary one fails (any AIServiceError). Empty
# disables the fallback entirely. Ignored when equal to AI_PROVIDER.
AI_FALLBACK_PROVIDER = env("AI_FALLBACK_PROVIDER", default="")

# Provider-specific defaults keep switching providers explicit and avoid
# accidentally sending a local request to a remote base URL (or vice versa).
GROQ_BASE_URL = env("GROQ_BASE_URL", default="https://api.groq.com/openai/v1")
GROQ_MODEL = env("GROQ_MODEL", default="openai/gpt-oss-20b")
GROQ_TIMEOUT_SECONDS = env("GROQ_TIMEOUT_SECONDS")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://ollama:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", default="qwen2.5:0.5b")
OLLAMA_TIMEOUT_SECONDS = env("OLLAMA_TIMEOUT_SECONDS")
OLLAMA_NUM_CTX = env("OLLAMA_NUM_CTX")
OLLAMA_KEEP_ALIVE = env("OLLAMA_KEEP_ALIVE", default="1m")

if AI_PROVIDER.strip().lower() == "groq":
    AI_MODEL = GROQ_MODEL
elif AI_PROVIDER.strip().lower() == "ollama":
    AI_MODEL = OLLAMA_MODEL

# Avoid accidental email delivery while the product is being developed.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Baseline security settings; production may opt in to HTTPS-only cookies.
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")
SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT")
