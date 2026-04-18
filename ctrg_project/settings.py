import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(BASE_DIR / ".env")


def env(name, default=None):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name, default=0):
    value = env(name)
    if value is None:
        return default
    return int(value)


def env_list(name, default=None):
    if default is None:
        default = []
    value = env(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def unique_values(items):
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def database_config():
    database_url = env("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        options = {}
        sslmode = query.get("sslmode", [None])[0]
        if sslmode:
            options["sslmode"] = sslmode
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 5432),
            "OPTIONS": options,
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }

    return {
        "ENGINE": env("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": env("DB_NAME", "ctrg_grant_system"),
        "USER": env("DB_USER", "ctrg_app"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 0),
    }


MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVE_MEDIA = env_bool("SERVE_MEDIA", False)

SECRET_KEY = env(
    "SECRET_KEY",
    "local-dev-only-9Yw2Lk7Qm4Hc8Vr1Nt6Px3Ba5Zd0Sf2Ju8Re1Gw4Kb7Cn9",
)
DEBUG = env_bool("DEBUG", True)

allowed_hosts = env_list("ALLOWED_HOSTS", ["127.0.0.1", "localhost"])
render_hostname = env("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    allowed_hosts.append(render_hostname)
ALLOWED_HOSTS = unique_values(allowed_hosts)

csrf_trusted_origins = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ["http://127.0.0.1:8000", "http://localhost:8000"],
)
if render_hostname:
    csrf_trusted_origins.append(f"https://{render_hostname}")
CSRF_TRUSTED_ORIGINS = unique_values(csrf_trusted_origins)

X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", "SAMEORIGIN")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ctrg_app",
    "django.contrib.sites",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "/"

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

ROOT_URLCONF = "ctrg_project.urls"

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
    },
]

WSGI_APPLICATION = "ctrg_project.wsgi.application"

DATABASES = {
    "default": database_config(),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

staticfiles_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"
if not DEBUG:
    staticfiles_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": staticfiles_backend,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "ctrg_app.Users"

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 20)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@example.com")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", False)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)
