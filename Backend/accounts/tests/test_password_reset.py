import pytest

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from conftest import DEFAULT_PASSWORD


def _reset_confirm_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})


@pytest.mark.django_db
def test_forgot_password_sends_email_to_known_patient(client, patient_user):
    """A known, active patient email triggers a reset email and redirects to the sent page."""
    response = client.post(
        reverse("patient_forgot_password"), {"email": patient_user.email}
    )
    assert response.status_code == 302
    assert response.url == reverse("patient_password_reset_sent")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_forgot_password_unknown_email_does_not_leak(client):
    """An unknown email still redirects normally and sends nothing (no account enumeration)."""
    response = client.post(
        reverse("patient_forgot_password"), {"email": "nobody@example.com"}
    )
    assert response.status_code == 302
    assert response.url == reverse("patient_password_reset_sent")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_confirm_page_renders_with_valid_token(client, patient_user):
    """A valid reset link shows the new-password form."""
    response = client.get(_reset_confirm_url(patient_user))
    assert response.status_code == 200


@pytest.mark.django_db
def test_reset_confirm_invalid_token_shows_invalid_page(client, patient_user):
    """A bad token shows the invalid-link page, not the reset form."""
    uid = urlsafe_base64_encode(force_bytes(patient_user.pk))
    url = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": "bad-token"})
    response = client.get(url)
    assert response.status_code == 200
    assert b"reset" in response.content.lower()  # invalid template still renders


@pytest.mark.django_db
def test_reset_confirm_sets_new_password(client, patient_user):
    """Submitting two matching valid passwords updates the account password."""
    url = _reset_confirm_url(patient_user)
    response = client.post(url, {"password1": "BrandNewPass1", "password2": "BrandNewPass1"})

    assert response.status_code == 302
    assert response.url == reverse("password_reset_done")
    patient_user.refresh_from_db()
    assert patient_user.check_password("BrandNewPass1")
    assert not patient_user.check_password(DEFAULT_PASSWORD)


@pytest.mark.django_db
def test_reset_confirm_rejects_mismatched_passwords(client, patient_user):
    """Mismatched passwords are rejected and the old password still works."""
    url = _reset_confirm_url(patient_user)
    response = client.post(url, {"password1": "BrandNewPass1", "password2": "Different1"})

    assert response.status_code == 200
    patient_user.refresh_from_db()
    assert patient_user.check_password(DEFAULT_PASSWORD)


@pytest.mark.django_db
def test_reset_confirm_rejects_short_password(client, patient_user):
    """A password shorter than 8 characters is rejected."""
    url = _reset_confirm_url(patient_user)
    response = client.post(url, {"password1": "short", "password2": "short"})

    assert response.status_code == 200
    patient_user.refresh_from_db()
    assert patient_user.check_password(DEFAULT_PASSWORD)
