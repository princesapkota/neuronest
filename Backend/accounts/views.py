from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

from accounts.models import Profile, Role, Sex


# -----------------------
# TEMPLATE PATHS
# -----------------------
TEMPLATE_LANDING = "index.html"
TEMPLATE_PATIENT_SIGNUP = "accounts/patient-signup.html"
TEMPLATE_VERIFY_SENT = "accounts/verify-email-sent.html"
TEMPLATE_VERIFY_SUCCESS = "accounts/verify-email-success.html"
TEMPLATE_VERIFY_FAILED = "accounts/verify-email-failed.html"


# -----------------------
# Landing
# -----------------------
def index(request):
    return render(request, TEMPLATE_LANDING)


# -----------------------
# Patient Signup
# -----------------------
def patient_signup(request):
    """
    Patient signup.
    Expects:
      full_name
      email
      hospital_patient_id
      sex
      age
      password
      confirm_password
    """

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        hospital_patient_id = request.POST.get("hospital_patient_id", "").strip()
        sex = request.POST.get("sex", "").strip()
        age = request.POST.get("age", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # Required validation
        if not all([full_name, email, hospital_patient_id, sex, age, password, confirm_password]):
            messages.error(request, "Please fill all fields.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Email uniqueness
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Hospital ID uniqueness
        if Profile.objects.filter(hospital_patient_id__iexact=hospital_patient_id).exists():
            messages.error(request, "This Hospital Patient ID is already registered.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Validate sex
        if sex not in [Sex.MALE, Sex.FEMALE, Sex.OTHER]:
            messages.error(request, "Invalid sex value.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Validate age
        try:
            age_int = int(age)
            if age_int <= 0 or age_int > 120:
                raise ValueError()
        except ValueError:
            messages.error(request, "Age must be a valid number between 1 and 120.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Create user (inactive until email verified)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
        )

        # Profile is created by signal, now update it
        profile = user.profile
        profile.full_name = full_name
        profile.hospital_patient_id = hospital_patient_id
        profile.sex = sex
        profile.age = age_int
        profile.role = Role.PATIENT
        profile.save()

        # Send verification email
        _send_verification_email(request, user)

        return redirect("verify_email_sent")

    return render(request, TEMPLATE_PATIENT_SIGNUP)


# -----------------------
# Verification Sent Page
# -----------------------
def verify_email_sent(request):
    return render(request, TEMPLATE_VERIFY_SENT)


# -----------------------
# Verify Email
# -----------------------
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        return render(request, TEMPLATE_VERIFY_FAILED)

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, TEMPLATE_VERIFY_SUCCESS)

    return render(request, TEMPLATE_VERIFY_FAILED)


# -----------------------
# Send Verification Email
# -----------------------
def _send_verification_email(request, user):
    current_site = get_current_site(request)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verify_path = reverse("verify_email", kwargs={"uidb64": uid, "token": token})
    verify_url = f"http://{current_site.domain}{verify_path}"

    subject = "Verify your NeuroNest account"
    message = (
        f"Hello {user.profile.full_name},\n\n"
        f"Please verify your email by clicking the link below:\n\n"
        f"{verify_url}\n\n"
        f"If you did not create this account, you can ignore this email.\n\n"
        f"- NeuroNest"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )