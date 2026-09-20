import os
from datetime import timedelta

from .base import *  # noqa: F403

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api"]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),     # Short-lived security token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),        # Long-lived token to get a new access token
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,                          # Signs the token cryptographic signature
    "AUTH_HEADER_TYPES": ("Bearer",),                   # Clients must send: 'Authorization: Bearer <token>'
    "USER_ID_FIELD": "email", 
    "USER_ID_CLAIM": "user_email",  # Embeds user email into the secure JWT claim footprint
    
}


