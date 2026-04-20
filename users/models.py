from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("doctor", "Doctor"),
        ("parent", "Parent"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    current_session_key = models.CharField(max_length=40, blank=True)


class OpenAISettings(models.Model):
    api_key = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "OpenAI Settings"
