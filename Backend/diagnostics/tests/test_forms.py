import pytest

from django.core.files.uploadedfile import SimpleUploadedFile

from diagnostics.forms import DiagnosticUploadForm
from diagnostics.models import DiagnosticResult


def _bind_form(patient_profile, model_type, filename):
    data = {"patient": patient_profile.id, "model_type": model_type}
    files = {"input_file": SimpleUploadedFile(filename, b"bytes")}
    return DiagnosticUploadForm(data=data, files=files)


@pytest.mark.django_db
def test_brain_tumor_accepts_nii(patient_user):
    """Brain tumor uploads accept NIfTI volumes."""
    form = _bind_form(patient_user.profile, DiagnosticResult.ModelType.BRAIN_TUMOR, "scan.nii")
    assert form.is_valid()


@pytest.mark.django_db
def test_brain_tumor_rejects_image(patient_user):
    """Brain tumor uploads reject ordinary image files."""
    form = _bind_form(patient_user.profile, DiagnosticResult.ModelType.BRAIN_TUMOR, "scan.jpg")
    assert not form.is_valid()


@pytest.mark.django_db
def test_pneumonia_accepts_jpg(patient_user):
    """Pneumonia uploads accept JPG x-rays."""
    form = _bind_form(patient_user.profile, DiagnosticResult.ModelType.PNEUMONIA, "xray.jpg")
    assert form.is_valid()


@pytest.mark.django_db
def test_pneumonia_rejects_nii(patient_user):
    """Pneumonia uploads reject NIfTI volumes."""
    form = _bind_form(patient_user.profile, DiagnosticResult.ModelType.PNEUMONIA, "scan.nii")
    assert not form.is_valid()


@pytest.mark.django_db
def test_fracture_accepts_png(patient_user):
    """Fracture uploads accept PNG x-rays."""
    form = _bind_form(patient_user.profile, DiagnosticResult.ModelType.FRACTURE, "bone.png")
    assert form.is_valid()
