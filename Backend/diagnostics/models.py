from django.db import models
from accounts.models import Profile


# this decides the folder path where an uploaded input file gets saved
def upload_input_to(instance, filename: str) -> str:
    # saves to media/<model_type>/inputs/<filename>
    return f"{instance.model_type}/inputs/{filename}"


# this is the main table that stores one diagnostic run, its input, its output image and where it is in the workflow
class DiagnosticResult(models.Model):
    # the three AI models we can run a scan through
    class ModelType(models.TextChoices):
        BRAIN_TUMOR = "brain_tumor", "Brain Tumor Segmentation"
        FRACTURE = "fracture", "Fracture Detection"
        PNEUMONIA = "pneumonia", "Pneumonia Classification"

    # the simple positive or negative answer
    class Verdict(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"

    # where the report is in the employee workflow
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FORWARDED = "forwarded", "Forwarded to Patient"
        REJECTED = "rejected", "Rejected"

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

    # Keep this for now so existing code does not break.
    # If you stop using it later, we can remove it safely in a later cleanup.
    verdict = models.CharField(
        max_length=20,
        choices=Verdict.choices,
        null=True,
        blank=True,
    )

    # New workflow field
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # INPUT stored on disk (MEDIA)
    input_file = models.FileField(upload_to=upload_input_to, null=True, blank=True)

    # OUTPUT PNG stored in DB
    output_png = models.BinaryField(null=True, blank=True)
    output_png_name = models.CharField(max_length=255, null=True, blank=True)
    output_png_content_type = models.CharField(max_length=50, default="image/png")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "-created_at"]),
            models.Index(fields=["model_type", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    # this saves the generated report image bytes onto the result row
    def set_output_png(self, png_bytes: bytes, filename: str = "result.png"):
        self.output_png = png_bytes
        self.output_png_name = filename
        self.output_png_content_type = "image/png"

    # this is the text shown for a result in the admin site and shell
    def __str__(self):
        patient_name = self.patient.full_name if self.patient else "Unknown Patient"
        return f"{self.model_type} | {patient_name} | {self.status} | {self.created_at.date()}"