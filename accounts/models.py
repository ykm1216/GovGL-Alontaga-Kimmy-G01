from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """GovGL user. Roles decide which dashboard a user can open."""

    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient / Beneficiary"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    contact_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.username
