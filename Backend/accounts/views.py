from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from .forms import PatientSignupForm
from .models import Role


def patient_signup(request):
    """
    Creates a patient user + profile, but keeps the account inactive until email verification.
    """
    if request.method == "POST":
        form = PatientSignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                email = form.cleaned_data["email"].lower()

                # Create User (auth_user)
                user = User.objects.create_user(
                    username=email,  # simplest: use email as username
                    email=email,
                    password=form.cleaned_data["password"],
                    is_active=False,  # must verify email first
                )

                # Update Profile created by your signals
                profile = user.profile
                profile.role = Role.PATIENT
                profile.full_name = form.cleaned_data["full_name"]
                profile.hospital_patient_id = form.cleaned_data["hospital_patient_id"]
                profile.sex = form.cleaned_data["sex"]
                profile.age = form.cleaned_data["age"]
                profile.save()

            # Send verification email
            send_verification_email(request, user)

            # Show "check your email" page
            return redirect("verify_email_sent")
    else:
        form = PatientSignupForm()

    return render(request, "accounts/patient-signup.html", {"form": form})


def verify_email_sent(request):
    """
    Simple page that tells user to check inbox.
    """
    return render(request, "accounts/verify-email-sent.html")


def send_verification_email(request, user: User):
    """
    Sends a verification link containing (uidb64, token).
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verify_link = request.build_absolute_uri(
        reverse("verify_email", kwargs={"uidb64": uidb64, "token": token})
    )

    subject = "Verify your NeuroNest account"
    message = (
        "Thanks for signing up for NeuroNest.\n\n"
        "Please verify your email by clicking the link below:\n"
        f"{verify_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def verify_email(request, uidb64, token):
    """
    When user clicks email link, validate token and activate account.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        return render(request, "accounts/verify-email-success.html")

    return render(request, "accounts/verify-email-failed.html")