from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from accounts.models import Profile, Role, Sex
from diagnostics.models import DiagnosticResult
from notifications.models import Notification


# these are just shortcuts to the template file names so we don't type the paths everywhere
TEMPLATE_LANDING = "index.html"
TEMPLATE_PATIENT_SIGNUP = "accounts/patient-signup.html"
TEMPLATE_VERIFY_SENT = "accounts/verify-email-sent.html"
TEMPLATE_VERIFY_SUCCESS = "accounts/verify-email-success.html"
TEMPLATE_VERIFY_FAILED = "accounts/verify-email-failed.html"
TEMPLATE_EMPLOYEE_DASHBOARD = "employee/dashboard.html"
TEMPLATE_PATIENT_DASHBOARD = "patient/patient-dashboard.html"
TEMPLATE_PATIENT_RESULTS = "patient/results.html"
TEMPLATE_PATIENT_NOTIFICATIONS = "patient/notifications.html"
TEMPLATE_PATIENT_RESULT_DETAIL = "patient/result-detail.html"


# this checks the logged in user is the role we expect (patient/employee/admin) before letting them in
def _require_role(user, role: str) -> bool:
    return hasattr(user, "profile") and user.profile.role == role


# this just shows the main landing/home page of the website
def index(request):
    return render(request, TEMPLATE_LANDING)


# this is the patient sign up page, it checks all the fields then makes the account and emails a verify link
def patient_signup(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        hospital_patient_id = request.POST.get("hospital_patient_id", "").strip()
        sex = request.POST.get("sex", "").strip()
        age = request.POST.get("age", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([full_name, email, hospital_patient_id, sex, age, password, confirm_password]):
            messages.error(request, "Please fill all fields.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if Profile.objects.filter(hospital_patient_id__iexact=hospital_patient_id).exists():
            messages.error(request, "This Hospital Patient ID is already registered.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        if sex not in [Sex.MALE, Sex.FEMALE, Sex.OTHER]:
            messages.error(request, "Invalid sex value.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        try:
            age_int = int(age)
            if age_int <= 0 or age_int > 120:
                raise ValueError
        except ValueError:
            messages.error(request, "Age must be between 1 and 120.")
            return render(request, TEMPLATE_PATIENT_SIGNUP)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
        )

        profile = user.profile
        profile.full_name = full_name
        profile.hospital_patient_id = hospital_patient_id
        profile.sex = sex
        profile.age = age_int
        profile.role = Role.PATIENT
        profile.save()

        _send_verification_email(request, user)

        return redirect("verify_email_sent")

    return render(request, TEMPLATE_PATIENT_SIGNUP)


# this is the little page that says check your email after signing up
def verify_email_sent(request):
    return render(request, TEMPLATE_VERIFY_SENT)


# this is where the email link lands, it checks the token and turns the account on if it is valid
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


# this loads the employee home dashboard, only employees are allowed
@login_required
def employee_dashboard(request):
    if not _require_role(request.user, Role.EMPLOYEE):
        return redirect("index")

    return render(request, TEMPLATE_EMPLOYEE_DASHBOARD)


# this loads the patient dashboard and counts their reports and unread notifications to show on it
@login_required
def patient_dashboard(request):
    if not _require_role(request.user, Role.PATIENT):
        return redirect("index")

    forwarded_count = DiagnosticResult.objects.filter(
        patient=request.user.profile,
        status=DiagnosticResult.Status.FORWARDED,
    ).count()

    unread_notifications_count = Notification.objects.filter(
        patient=request.user.profile,
        is_read=False,
    ).count()

    recent_notifications = Notification.objects.filter(
        patient=request.user.profile
    ).select_related("result").order_by("-created_at")[:5]

    return render(
        request,
        TEMPLATE_PATIENT_DASHBOARD,
        {
            "forwarded_count": forwarded_count,
            "unread_notifications_count": unread_notifications_count,
            "recent_notifications": recent_notifications,
        },
    )


# this lists all the reports that have been forwarded to the logged in patient
@login_required
def patient_results(request):
    if not _require_role(request.user, Role.PATIENT):
        return redirect("index")

    results = DiagnosticResult.objects.filter(
        patient=request.user.profile,
        status=DiagnosticResult.Status.FORWARDED,
    ).order_by("-created_at")

    return render(request, TEMPLATE_PATIENT_RESULTS, {"results": results})


# this opens one single report for the patient, only if it really belongs to them
@login_required
def patient_result_detail(request, result_id):
    if not _require_role(request.user, Role.PATIENT):
        return redirect("index")

    result = get_object_or_404(
        DiagnosticResult,
        id=result_id,
        patient=request.user.profile,
        status=DiagnosticResult.Status.FORWARDED,
    )

    return render(request, TEMPLATE_PATIENT_RESULT_DETAIL, {"result": result})


# this shows the patients notifications and marks the unread ones as read when they open the page
@login_required
def patient_notifications(request):
    if not _require_role(request.user, Role.PATIENT):
        return redirect("index")

    notifications = Notification.objects.filter(
        patient=request.user.profile
    ).select_related("result").order_by("-created_at")

    unread_ids = list(
        notifications.filter(is_read=False).values_list("id", flat=True)
    )

    if unread_ids:
        Notification.objects.filter(id__in=unread_ids).update(is_read=True)

    return render(request, TEMPLATE_PATIENT_NOTIFICATIONS, {"notifications": notifications})


# this builds the verify link with a safe token and emails it to the new user
def _send_verification_email(request, user):
    current_site = get_current_site(request)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verify_path = reverse("verify_email", kwargs={"uidb64": uid, "token": token})
    verify_url = f"http://{current_site.domain}{verify_path}"

    subject = "Verify your NeuroNest account"
    message = (
        f"Hello {user.profile.full_name},\n\n"
        f"Verify your email:\n{verify_url}\n\n"
        f"- NeuroNest"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
