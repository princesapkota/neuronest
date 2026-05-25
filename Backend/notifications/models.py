from django.db import models
from accounts.models import Profile
from diagnostics.models import DiagnosticResult


# this is one message sent to a patient, usually telling them a new report is ready
class Notification(models.Model):
    patient = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="notifications",
        limit_choices_to={"role": "patient"},
    )

    # ties the notification to the exact result it is about
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

    # this is the text shown for a notification in the admin site and shell
    def __str__(self):
        return f"{self.title} -> {self.patient.full_name}"