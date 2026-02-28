from django.db import models
from accounts.models import Profile


class DiagnosticResult(models.Model):
    class ModelType(models.TextChoices):
        BRAIN_TUMOR = "brain_tumor", "Brain Tumor Segmentation"
        FRACTURE = "fracture", "Fracture Detection"
        PNEUMONIA = "pneumonia", "Pneumonia Classification"

    class Verdict(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"

    # who the result belongs to
    patient = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="results_received",
        limit_choices_to={"role": "patient"},
    )


    employee = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results_created",
        limit_choices_to={"role": "employee"},
    )

    model_type = models.CharField(max_length=30, choices=ModelType.choices)



    verdict = models.CharField(max_length=20, choices=Verdict.choices)



    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "-created_at"]),
            models.Index(fields=["model_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.model_type} | {self.patient.full_name} | {self.created_at.date()}"