import pytest

from django.contrib.auth.models import User

from accounts.models import Profile, Role


@pytest.mark.django_db
def test_creating_user_auto_creates_profile():
    """The post_save signal gives every new User a Profile (defaults to patient)."""
    user = User.objects.create_user(username="auto", password="x")
    assert hasattr(user, "profile")
    assert user.profile.role == Role.PATIENT


@pytest.mark.django_db
def test_signal_does_not_overwrite_existing_profile_role(employee_user):
    """Re-saving a User must not reset an already-assigned role back to patient."""
    employee_user.first_name = "Changed"
    employee_user.save()
    employee_user.refresh_from_db()
    assert employee_user.profile.role == Role.EMPLOYEE


@pytest.mark.django_db
def test_profile_str_shows_name_and_role(patient_user):
    """__str__ is what the admin site and shell display for a profile."""
    assert str(patient_user.profile) == "Pat Patient (patient)"
