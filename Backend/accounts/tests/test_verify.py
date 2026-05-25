import pytest

from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def _verify_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("verify_email", kwargs={"uidb64": uid, "token": token})


@pytest.mark.django_db
def test_valid_link_activates_account(client, make_user):
    """A correct uid+token activates the previously inactive account."""
    user = make_user("verifyme", is_active=False)
    response = client.get(_verify_url(user))

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_invalid_token_does_not_activate(client, make_user):
    """A tampered token leaves the account inactive and shows the failure page."""
    user = make_user("badtoken", is_active=False)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    bad_url = reverse("verify_email", kwargs={"uidb64": uid, "token": "not-a-real-token"})

    response = client.get(bad_url)

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is False


@pytest.mark.django_db
def test_malformed_uid_shows_failure(client):
    """A garbage uid is handled gracefully rather than crashing."""
    bad_url = reverse("verify_email", kwargs={"uidb64": "@@@", "token": "abc"})
    response = client.get(bad_url)
    assert response.status_code == 200
