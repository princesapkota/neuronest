from django.db import models
from accounts.models import Profile
from diagnostics.models import DiagnosticResult


class Notification(models.Model):
    patient = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="notifications",
        limit_choices_to={"role": "patient"},
    )

    # Link notification to a specific result
    result = models.ForeignKey(
        DiagnosticResult,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=120)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} -> {self.patient.full_name}"