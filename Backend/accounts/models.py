from django.db import models
from django.contrib.auth.models import User


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    EMPLOYEE = "employee", "Employee"
    PATIENT = "patient", "Patient"


class Sex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(max_length=20, choices=Role.choices)
    full_name = models.CharField(max_length=150)

    # Patient-only fields
    hospital_patient_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    sex = models.CharField(
        max_length=10,
        choices=Sex.choices,
        null=True,
        blank=True
    )

    age = models.PositiveIntegerField(
        null=True,
        blank=True
    )
  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"