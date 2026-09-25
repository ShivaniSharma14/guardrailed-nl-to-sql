import os

import dj_database_url

from .base import *  # noqa: F403

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

ALLOWED_HOSTS = [
    h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h
]
# Render sets this automatically for the service's own onrender.com domain
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)

DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"])
}

# Static files served directly by WhiteNoise from the Django process —
# no separate nginx/CDN needed at this scale.
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# CORS: explicit allowlist only, no wildcard — filled in once the frontend
# has a real deployed origin.
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

# HTTPS enforcement — Render terminates TLS in front of your container, so
# Django needs to know to trust the forwarded protocol header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True