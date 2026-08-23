import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractUser):
    # Use UUID primary key to avoid exposing sequential database IDs in URLs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Remove the username field completely
    username = None

    # Make email unique and required
    email = models.EmailField(unique=True)

    # Tell Django to use email as the unique identifier for logging in
    USERNAME_FIELD = "email"

    # Fields required when running 'createsuperuser' (email/password are automatic)
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
