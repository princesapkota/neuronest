import pytest

from django.urls import reverse

from diagnostics.models import DiagnosticResult
from notifications.models import Notification


def _make_result(patient, employee, status):
    return DiagnosticResult.objects.create(
        patient=patient.profile,
        employee=employee.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
        status=status,
    )


@pytest.mark.django_db
def test_dashboard_counts_forwarded_and_unread(patient_client, patient_user, employee_user):
    """The dashboard reports how many forwarded results and unread notifications a patient has."""
    forwarded = _make_result(patient_user, employee_user, DiagnosticResult.Status.FORWARDED)
    _make_result(patient_user, employee_user, DiagnosticResult.Status.DRAFT)  # not counted
    Notification.objects.create(
        patient=patient_user.profile, result=forwarded, title="t", message="m", is_read=False
    )

    response = patient_client.get(reverse("patient_dashboard"))

    assert response.status_code == 200
    assert response.context["forwarded_count"] == 1
    assert response.context["unread_notifications_count"] == 1


@pytest.mark.django_db
def test_dashboard_blocks_non_patient(employee_client):
    """An employee hitting the patient dashboard is redirected away."""
    response = employee_client.get(reverse("patient_dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("index")


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    """An anonymous visitor is redirected to log in."""
    response = client.get(reverse("patient_dashboard"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_results_lists_only_forwarded(patient_client, patient_user, employee_user):
    """The results page shows forwarded reports only, never drafts or rejected ones."""
    _make_result(patient_user, employee_user, DiagnosticResult.Status.FORWARDED)
    _make_result(patient_user, employee_user, DiagnosticResult.Status.DRAFT)
    _make_result(patient_user, employee_user, DiagnosticResult.Status.REJECTED)

    response = patient_client.get(reverse("patient_results"))

    assert response.status_code == 200
    assert len(response.context["results"]) == 1


@pytest.mark.django_db
def test_result_detail_visible_when_owned_and_forwarded(patient_client, patient_user, employee_user):
    """A patient can open their own forwarded report."""
    result = _make_result(patient_user, employee_user, DiagnosticResult.Status.FORWARDED)
    response = patient_client.get(
        reverse("patient_result_detail", kwargs={"result_id": result.id})
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_result_detail_404_when_not_forwarded(patient_client, patient_user, employee_user):
    """A draft report (not yet forwarded) is not viewable by the patient."""
    result = _make_result(patient_user, employee_user, DiagnosticResult.Status.DRAFT)
    response = patient_client.get(
        reverse("patient_result_detail", kwargs={"result_id": result.id})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_result_detail_404_for_other_patients_report(patient_client, employee_user, make_user):
    """A patient cannot open a report that belongs to someone else."""
    other = make_user("otherpat", hospital_patient_id="HP-OTHER")
    result = _make_result(other, employee_user, DiagnosticResult.Status.FORWARDED)
    response = patient_client.get(
        reverse("patient_result_detail", kwargs={"result_id": result.id})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_notifications_page_marks_unread_as_read(patient_client, patient_user, employee_user):
    """Opening the notifications page marks the patient's unread notifications as read."""
    result = _make_result(patient_user, employee_user, DiagnosticResult.Status.FORWARDED)
    Notification.objects.create(
        patient=patient_user.profile, result=result, title="t", message="m", is_read=False
    )

    response = patient_client.get(reverse("patient_notifications"))

    assert response.status_code == 200
    assert Notification.objects.filter(patient=patient_user.profile, is_read=False).count() == 0
