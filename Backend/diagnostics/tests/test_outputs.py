import io

import pytest
from PIL import Image

from django.urls import reverse

from diagnostics.models import DiagnosticResult


def _real_png_bytes():
    """A genuine (tiny) PNG so reportlab can embed it in the PDF test."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (200, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _result_with_png(patient, employee):
    result = DiagnosticResult.objects.create(
        patient=patient.profile,
        employee=employee.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
        status=DiagnosticResult.Status.FORWARDED,
    )
    result.set_output_png(_real_png_bytes(), filename="report.png")
    result.save()
    return result


@pytest.mark.django_db
def test_output_png_returns_stored_image(client, patient_user, employee_user):
    """The PNG endpoint serves the stored report image with an image content type."""
    result = _result_with_png(patient_user, employee_user)
    response = client.get(reverse("diagnostics:diagnostic_output_png", kwargs={"result_id": result.id}))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content == result.output_png


@pytest.mark.django_db
def test_output_png_404_when_missing(client, patient_user, employee_user):
    """Requesting the PNG before one exists returns 404."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
    )
    response = client.get(reverse("diagnostics:diagnostic_output_png", kwargs={"result_id": result.id}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_output_pdf_returns_pdf(client, patient_user, employee_user):
    """The PDF endpoint returns a downloadable PDF built from the stored report image."""
    result = _result_with_png(patient_user, employee_user)
    response = client.get(reverse("diagnostics:diagnostic_output_pdf", kwargs={"result_id": result.id}))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
