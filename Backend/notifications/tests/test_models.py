import pytest

from diagnostics.models import DiagnosticResult
from notifications.models import Notification


@pytest.mark.django_db
def test_notification_defaults_to_unread(patient_user, employee_user):
    """A new notification starts unread."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
    )
    note = Notification.objects.create(
        patient=patient_user.profile, result=result, title="Report ready", message="..."
    )
    assert note.is_read is False


@pytest.mark.django_db
def test_notification_str_points_title_to_patient(patient_user, employee_user):
    """__str__ reads as 'title -> patient name' for the admin site and shell."""
    result = DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
    )
    note = Notification.objects.create(
        patient=patient_user.profile, result=result, title="Report ready", message="..."
    )
    assert str(note) == "Report ready -> Pat Patient"
