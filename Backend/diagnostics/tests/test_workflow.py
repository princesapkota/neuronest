import pytest

from django.test import Client
from django.urls import reverse

from accounts.models import Role
from diagnostics.models import DiagnosticResult
from notifications.models import Notification


def _draft(patient, employee):
    return DiagnosticResult.objects.create(
        patient=patient.profile,
        employee=employee.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
        status=DiagnosticResult.Status.DRAFT,
    )


@pytest.mark.django_db
def test_forward_sets_status_and_notifies_patient(employee_client, patient_user, employee_user):
    """Forwarding a report marks it forwarded and creates a patient notification."""
    result = _draft(patient_user, employee_user)
    url = reverse("diagnostics:forward_report_to_patient", kwargs={"result_id": result.id})

    response = employee_client.post(url)

    assert response.status_code == 302
    result.refresh_from_db()
    assert result.status == DiagnosticResult.Status.FORWARDED
    assert Notification.objects.filter(patient=patient_user.profile, result=result).count() == 1


@pytest.mark.django_db
def test_forward_twice_does_not_duplicate_notification(employee_client, patient_user, employee_user):
    """Re-forwarding an already-forwarded report does not create a second notification."""
    result = _draft(patient_user, employee_user)
    url = reverse("diagnostics:forward_report_to_patient", kwargs={"result_id": result.id})

    employee_client.post(url)
    employee_client.post(url)

    assert Notification.objects.filter(result=result).count() == 1


@pytest.mark.django_db
def test_forward_requires_post(employee_client, patient_user, employee_user):
    """A GET on the forward endpoint does not change the report."""
    result = _draft(patient_user, employee_user)
    url = reverse("diagnostics:forward_report_to_patient", kwargs={"result_id": result.id})

    response = employee_client.get(url)

    assert response.status_code == 302
    result.refresh_from_db()
    assert result.status == DiagnosticResult.Status.DRAFT


@pytest.mark.django_db
def test_reject_sets_status_rejected(employee_client, patient_user, employee_user):
    """Rejecting a report marks it rejected and creates no patient notification."""
    result = _draft(patient_user, employee_user)
    url = reverse("diagnostics:reject_report", kwargs={"result_id": result.id})

    response = employee_client.post(url)

    assert response.status_code == 302
    result.refresh_from_db()
    assert result.status == DiagnosticResult.Status.REJECTED
    assert Notification.objects.filter(result=result).count() == 0


@pytest.mark.django_db
def test_employee_cannot_forward_another_employees_report(
    patient_user, employee_user, make_user
):
    """An employee can only act on reports they created; others get a 404."""
    result = _draft(patient_user, employee_user)

    other = make_user("employee2", role=Role.EMPLOYEE)
    other_client = Client()
    other_client.force_login(other)

    url = reverse("diagnostics:forward_report_to_patient", kwargs={"result_id": result.id})
    response = other_client.post(url)

    assert response.status_code == 404
    result.refresh_from_db()
    assert result.status == DiagnosticResult.Status.DRAFT
