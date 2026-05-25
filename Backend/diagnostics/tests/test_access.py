import pytest

from django.urls import reverse


EMPLOYEE_ONLY_VIEWS = ["diagnostics:employee_upload", "diagnostics:employee_reports"]


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", EMPLOYEE_ONLY_VIEWS)
def test_patient_redirected_from_employee_pages(patient_client, url_name):
    """A logged-in patient is redirected away from employee-only pages."""
    response = patient_client.get(reverse(url_name))
    assert response.status_code == 302
    assert response.url == reverse("index")


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", EMPLOYEE_ONLY_VIEWS)
def test_anonymous_redirected_from_employee_pages(client, url_name):
    """An anonymous visitor is redirected (to log in) from employee-only pages."""
    response = client.get(reverse(url_name))
    assert response.status_code == 302


@pytest.mark.django_db
def test_employee_reports_lists_only_own_reports(employee_client, patient_user, employee_user, make_user):
    """The reports page shows only the logged-in employee's own reports."""
    from diagnostics.models import DiagnosticResult
    from accounts.models import Role

    DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=employee_user.profile,
        model_type=DiagnosticResult.ModelType.PNEUMONIA,
    )
    other_employee = make_user("employee3", role=Role.EMPLOYEE)
    DiagnosticResult.objects.create(
        patient=patient_user.profile,
        employee=other_employee.profile,
        model_type=DiagnosticResult.ModelType.FRACTURE,
    )

    response = employee_client.get(reverse("diagnostics:employee_reports"))

    assert response.status_code == 200
    assert len(response.context["results"]) == 1
