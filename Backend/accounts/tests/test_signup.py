import pytest

from django.core import mail
from django.urls import reverse

from accounts.models import Profile, Role


def _valid_payload(**overrides):
    data = {
        "full_name": "New Patient",
        "email": "newpatient@example.com",
        "hospital_patient_id": "HP-999",
        "sex": "female",
        "age": "28",
        "password": "StrongPass123",
        "confirm_password": "StrongPass123",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_signup_page_renders(client):
    """GET on the signup page returns the form."""
    response = client.get(reverse("patient_signup"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_signup_valid_creates_inactive_user_and_sends_email(client):
    """A valid signup creates an inactive patient and emails a verification link."""
    response = client.post(reverse("patient_signup"), _valid_payload())

    assert response.status_code == 302
    assert response.url == reverse("verify_email_sent")

    profile = Profile.objects.get(hospital_patient_id="HP-999")
    assert profile.role == Role.PATIENT
    assert profile.full_name == "New Patient"
    assert profile.age == 28
    assert profile.user.is_active is False  # must verify email first
    assert len(mail.outbox) == 1
    assert "newpatient@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_signup_password_mismatch_shows_error(client):
    """Mismatched passwords are rejected and no account is created."""
    response = client.post(
        reverse("patient_signup"),
        _valid_payload(confirm_password="different"),
    )
    assert response.status_code == 200
    assert not Profile.objects.filter(hospital_patient_id="HP-999").exists()


@pytest.mark.django_db
def test_signup_duplicate_email_rejected(client, make_user):
    """An email already in use cannot be reused for signup."""
    make_user("existing", email="newpatient@example.com")
    response = client.post(reverse("patient_signup"), _valid_payload())
    assert response.status_code == 200
    # only the pre-existing user exists; signup did not create a second one
    assert not Profile.objects.filter(hospital_patient_id="HP-999").exists()


@pytest.mark.django_db
def test_signup_duplicate_hospital_id_rejected(client, make_user):
    """The hospital patient ID must be unique across patients."""
    make_user("other", role=Role.PATIENT, hospital_patient_id="HP-999")
    response = client.post(
        reverse("patient_signup"),
        _valid_payload(email="fresh@example.com"),
    )
    assert response.status_code == 200
    assert not Profile.objects.filter(user__email="fresh@example.com").exists()


@pytest.mark.django_db
def test_signup_invalid_age_rejected(client):
    """Age outside 1-120 is rejected."""
    response = client.post(reverse("patient_signup"), _valid_payload(age="200"))
    assert response.status_code == 200
    assert not Profile.objects.filter(hospital_patient_id="HP-999").exists()


@pytest.mark.django_db
def test_signup_missing_fields_rejected(client):
    """Leaving a required field blank is rejected."""
    response = client.post(reverse("patient_signup"), _valid_payload(full_name=""))
    assert response.status_code == 200
    assert not Profile.objects.filter(hospital_patient_id="HP-999").exists()
    assert len(mail.outbox) == 0
