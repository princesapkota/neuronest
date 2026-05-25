import pytest

from diagnostics.models import DiagnosticResult


@pytest.mark.django_db
def test_set_output_png_stores_bytes_and_metadata(patient_user, employee_user):
    """set_output_png saves the report image bytes and its filename onto the row."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.FRACTURE,
    )
    result.set_output_png(b"\x89PNGdata", filename="fracture_report_1.png")

    assert result.output_png == b"\x89PNGdata"
    assert result.output_png_name == "fracture_report_1.png"
    assert result.output_png_content_type == "image/png"


@pytest.mark.django_db
def test_default_status_is_draft(patient_user, employee_user):
    """A freshly created result starts life as a draft."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
    )
    assert result.status == DiagnosticResult.Status.DRAFT


@pytest.mark.django_db
def test_str_includes_model_patient_and_status(patient_user, employee_user):
    """__str__ summarises the result for the admin site and shell."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
        status=DiagnosticResult.Status.FORWARDED,
    )
    text = str(result)
    assert "pneumonia" in text
    assert "Pat Patient" in text
    assert "forwarded" in text
