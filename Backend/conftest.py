"""Shared pytest fixtures for the NeuroNest test suite.

These build the three kinds of accounts the app supports (admin, employee,
patient) plus ready-to-use logged-in test clients, so individual tests don't
repeat the setup boilerplate.
"""
import pytest
from django.contrib.auth.models import User
from django.test import Client

from accounts.models import Profile, Role

DEFAULT_PASSWORD = "TestPass123!"


@pytest.fixture
def make_user(db):
    """Factory that creates a User + its Profile with a given role.

    The post_save signal already creates a blank patient Profile, so here we
    just fill in the role and any extra profile fields the test cares about.
    """
    created = []

    def _make(username, *, role=Role.PATIENT, password=DEFAULT_PASSWORD,
              email=None, is_active=True, **profile_fields):
        email = email or f"{username}@example.com"
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_active = is_active
        user.save()

        profile = user.profile  # auto-created by the signal
        profile.role = role
        if "full_name" not in profile_fields:
            profile.full_name = username.title()
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        profile.save()

        created.append(user)
        return user

    return _make


@pytest.fixture
def patient_user(make_user):
    return make_user(
        "patient1",
        role=Role.PATIENT,
        full_name="Pat Patient",
        hospital_patient_id="HP-001",
        sex="male",
        age=30,
    )


@pytest.fixture
def employee_user(make_user):
    return make_user("employee1", role=Role.EMPLOYEE, full_name="Emma Employee")


@pytest.fixture
def admin_user(make_user):
    return make_user("admin1", role=Role.ADMIN, full_name="Adam Admin")


def _logged_in_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def patient_client(patient_user):
    return _logged_in_client(patient_user)


@pytest.fixture
def employee_client(employee_user):
    return _logged_in_client(employee_user)


@pytest.fixture
def admin_client(admin_user):
    return _logged_in_client(admin_user)
