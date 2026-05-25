import pytest

from django.core import mail
from django.urls import reverse

from accounts.models import Profile, Role


def _employee_payload(**overrides):
    data = {
        "full_name": "Created Employee",
        "personal_email": "personal@example.com",
        "assigned_email": "work@example.com",
        "password": "EmpPass1234",
        "confirm_password": "EmpPass1234",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_admin_dashboard_allows_admin(admin_client):
    """An admin can open the admin dashboard."""
    response = admin_client.get(reverse("portaladmin_dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_dashboard_blocks_non_admin(patient_client):
    """A patient cannot reach the admin dashboard."""
    response = patient_client.get(reverse("portaladmin_dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("index")


@pytest.mark.django_db
def test_create_employee_makes_active_employee_and_emails_credentials(admin_client):
    """Creating an employee makes an active employee account and emails their credentials."""
    response = admin_client.post(reverse("create_employee"), _employee_payload())

    assert response.status_code == 302
    assert response.url == reverse("employees_list")

    profile = Profile.objects.get(user__email="work@example.com")
    assert profile.role == Role.EMPLOYEE
    assert profile.user.is_active is True
    assert profile.personal_email == "personal@example.com"
    assert len(mail.outbox) == 1
    assert "personal@example.com" in mail.outbox[0].to  # creds go to personal inbox


@pytest.mark.django_db
def test_create_employee_password_mismatch_rejected(admin_client):
    """Mismatched passwords prevent employee creation."""
    response = admin_client.post(
        reverse("create_employee"), _employee_payload(confirm_password="nope")
    )
    assert response.status_code == 200
    assert not Profile.objects.filter(user__email="work@example.com").exists()


@pytest.mark.django_db
def test_create_employee_duplicate_assigned_email_rejected(admin_client, make_user):
    """An assigned email already in use is rejected."""
    make_user("taken", email="work@example.com")
    response = admin_client.post(reverse("create_employee"), _employee_payload())
    assert response.status_code == 200


@pytest.mark.django_db
def test_employees_list_search_filters(admin_client, make_user):
    """The employee list search box filters by name."""
    make_user("alice", role=Role.EMPLOYEE, full_name="Alice Anderson")
    make_user("bob", role=Role.EMPLOYEE, full_name="Bob Brown")

    response = admin_client.get(reverse("employees_list"), {"q": "Alice"})

    assert response.status_code == 200
    names = [p.full_name for p in response.context["employees"]]
    assert "Alice Anderson" in names
    assert "Bob Brown" not in names


@pytest.mark.django_db
def test_delete_employee_requires_post(admin_client, make_user):
    """Deleting an employee is POST-only; a GET is not allowed."""
    emp = make_user("todelete", role=Role.EMPLOYEE)
    url = reverse("delete_employee", kwargs={"profile_id": emp.profile.id})

    get_response = admin_client.get(url)
    assert get_response.status_code == 405  # GET blocked by require_POST
    assert Profile.objects.filter(id=emp.profile.id).exists()

    post_response = admin_client.post(url)
    assert post_response.status_code == 302
    assert not Profile.objects.filter(id=emp.profile.id).exists()


@pytest.mark.django_db
def test_patients_list_blocks_non_admin(employee_client):
    """An employee cannot view the admin patients list."""
    response = employee_client.get(reverse("patients_list"))
    assert response.status_code == 302
    assert response.url == reverse("index")


@pytest.mark.django_db
def test_delete_patient_removes_account(admin_client, make_user):
    """An admin can delete a patient account via POST."""
    patient = make_user("delpat", role=Role.PATIENT, hospital_patient_id="HP-DEL")
    url = reverse("delete_patient", kwargs={"profile_id": patient.profile.id})

    response = admin_client.post(url)

    assert response.status_code == 302
    assert not Profile.objects.filter(id=patient.profile.id).exists()
