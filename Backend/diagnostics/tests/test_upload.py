import pytest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

import diagnostics.views as dviews
from diagnostics.models import DiagnosticResult


@pytest.mark.django_db
def test_employee_upload_runs_model_and_creates_draft(
    employee_client, patient_user, employee_user, settings, tmp_path, monkeypatch
):
    """A valid pneumonia upload creates a draft result and stores the generated report PNG.

    The real ML inference is mocked so the test never loads PyTorch or checkpoints.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr(
        dviews, "build_pneumonia_report_png",
        lambda path: (b"\x89PNG-generated", {"label": "NORMAL"}),
    )

    upload = SimpleUploadedFile("xray.jpg", b"rawbytes", content_type="image/jpeg")
    response = employee_client.post(
        reverse("diagnostics:employee_upload"),
        {
            "patient": patient_user.profile.id,
            "model_type": DiagnosticResult.ModelType.PNEUMONIA,
            "input_file": upload,
        },
    )

    assert response.status_code == 302
    result = DiagnosticResult.objects.get()
    assert result.status == DiagnosticResult.Status.DRAFT
    assert result.employee == employee_user.profile
    assert result.patient == patient_user.profile
    assert bytes(result.output_png) == b"\x89PNG-generated"  # bytea comes back as memoryview


@pytest.mark.django_db
def test_employee_upload_page_renders(employee_client):
    """GET on the upload page shows the form."""
    response = employee_client.get(reverse("diagnostics:employee_upload"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_blocked_for_non_employee(patient_client):
    """A patient cannot access the employee upload page."""
    response = patient_client.get(reverse("diagnostics:employee_upload"))
    assert response.status_code == 302
    assert response.url == reverse("index")
