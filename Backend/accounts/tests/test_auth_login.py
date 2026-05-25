import pytest

from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Role
from conftest import DEFAULT_PASSWORD


@pytest.mark.django_db
def test_patient_logs_into_patient_portal(client, patient_user):
    """Correct patient credentials on the patient portal log in and redirect to the dashboard."""
    response = client.post(
        reverse("patient_login"),
        {"username": patient_user.username, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == reverse("patient_dashboard")


@pytest.mark.django_db
def test_login_works_with_email_identifier(client, patient_user):
    """A user can log in using their email instead of their username."""
    response = client.post(
        reverse("patient_login"),
        {"username": patient_user.email, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == reverse("patient_dashboard")


@pytest.mark.django_db
def test_employee_cannot_use_patient_portal(client, employee_user):
    """Right credentials but wrong portal is denied (role mismatch)."""
    response = client.post(
        reverse("patient_login"),
        {"username": employee_user.username, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200  # re-rendered with an error, not redirected
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_invalid_credentials_rejected(client, patient_user):
    """A wrong password does not log the user in."""
    response = client.post(
        reverse("patient_login"),
        {"username": patient_user.username, "password": "wrongpassword"},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_inactive_account_cannot_log_in(client, make_user):
    """An unverified (inactive) account is blocked from logging in."""
    user = make_user("inactivepat", role=Role.PATIENT, is_active=False)
    response = client.post(
        reverse("patient_login"),
        {"username": user.username, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_superuser_is_blocked_from_portal_login(client):
    """Superusers must use Django admin, not the portal login pages."""
    User.objects.create_superuser(
        username="root", email="root@example.com", password=DEFAULT_PASSWORD
    )
    response = client.post(
        reverse("portaladmin_login"),
        {"username": "root", "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_already_logged_in_patient_is_redirected_from_login_page(patient_client):
    """Visiting the login page while already authenticated sends you to your dashboard."""
    response = patient_client.get(reverse("patient_login"))
    assert response.status_code == 302
    assert response.url == reverse("patient_dashboard")


@pytest.mark.django_db
def test_logout_clears_session(patient_client):
    """Logout ends the session and redirects home."""
    response = patient_client.get(reverse("logout"))
    assert response.status_code == 302
    assert response.url == reverse("index")
    assert "_auth_user_id" not in patient_client.session
