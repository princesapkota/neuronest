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


TEMPLATE_LANDING = "index.html"                  # change if your landing filename is different
TEMPLATE_PATIENT_SIGNUP = "accounts/patient-signup.html"    # change if your filename is different
TEMPLATE_VERIFY_SENT = "accounts/verify-email-sent.html"    # change if your filename is different


def index(request):
    return render(request, TEMPLATE_LANDING)


def patient_signup(request):
    """
    Patient signup (self signup).
    Expects POST fields:
      full_name, email, sex, age, password1, password2
    """
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        sex = request.POST.get("sex", "").strip()
        age = request.POST.get("age", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not all([full_name, email, sex, age, password1, password2]):
            messages.error(request, "Please fill all fields.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        try:
            age_int = int(age)
            if age_int <= 0 or age_int > 120:
                raise ValueError()
        except ValueError:
            messages.error(request, "Age must be a valid number.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        # Create user (we use email as username for simplicity)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password1,
            is_active=False,  # email verification required
        )

        # Fill profile
        user.profile.full_name = full_name
        user.profile.sex = sex
        user.profile.age = age_int
        user.profile.role = "patient"
        user.profile.save()

        _send_verification_email(request, user)
        return redirect("verify_email_sent")

    return render(request, TEMPLATE_PATIENT_SIGNUP)


def verify_email_sent(request):
    return render(request, TEMPLATE_VERIFY_SENT)


def verify_email(request, uidb64, token):
    """
    Verify email link -> activate user.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Email verified. You can now log in.")
        return redirect("patient_login")

    messages.error(request, "Verification link is invalid or expired.")
    return redirect("index")


def _send_verification_email(request, user):
    current_site = get_current_site(request)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verify_path = reverse("verify_email", kwargs={"uidb64": uid, "token": token})
    verify_url = f"http://{current_site.domain}{verify_path}"

    subject = "Verify your NeuroNest account"
    message = (
        f"Hi {user.profile.full_name},\n\n"
        f"Please verify your email by clicking the link below:\n"
        f"{verify_url}\n\n"
        f"If you did not create this account, ignore this email."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )