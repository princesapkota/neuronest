from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings


# this is the shared login brain for all three portals, it logs the user in only if their role matches the page
def _role_login(request, template_name: str, required_role: str, success_url_name: str):
    """
    Shared role-based login handler for:
    - portal admin
    - employee
    - patient

    Behavior:
    - If already logged in as Django admin/superuser, log out and reload the page
    - If already logged in as a normal portal user, redirect to their dashboard
    - Authenticate with username first, then email if needed
    - Only allow login if the user's role matches the portal
    """

    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            logout(request)
            return redirect(request.path)

        try:
            role = request.user.profile.role
            if role == "admin":
                return redirect("portaladmin_dashboard")
            if role == "employee":
                return redirect("employee_dashboard")
            if role == "patient":
                return redirect("patient_dashboard")
        except Exception:
            logout(request)
            return redirect("index")

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=identifier, password=password)

        if user is None:
            try:
                matched_user = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=matched_user.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            messages.error(request, "Invalid credentials.")
            return render(request, template_name)

        if not user.is_active:
            messages.error(request, "Account inactive. Please verify email or contact admin.")
            return render(request, template_name)

        if user.is_superuser or user.is_staff:
            messages.error(request, "Please use the Django Admin (/admin/) to log in as superuser.")
            return render(request, template_name)

        try:
            role = user.profile.role
        except Exception:
            messages.error(request, "Profile missing. Contact support.")
            return render(request, template_name)

        if role != required_role:
            messages.error(request, "Access denied for this portal.")
            return render(request, template_name)

        login(request, user)
        return redirect(success_url_name)

    return render(request, template_name)


# this connects the admin login page to the shared login brain
def portaladmin_login_view(request):
    return _role_login(
        request=request,
        template_name="admin_ui/admin-login.html",
        required_role="admin",
        success_url_name="portaladmin_dashboard",
    )


# this connects the employee login page to the shared login brain
def employee_login_view(request):
    return _role_login(
        request=request,
        template_name="employee/employee-login.html",
        required_role="employee",
        success_url_name="employee_dashboard",
    )


# this connects the patient login page to the shared login brain
def patient_login_view(request):
    return _role_login(
        request=request,
        template_name="patient/patient-login.html",
        required_role="patient",
        success_url_name="patient_dashboard",
    )


# this logs the user out and clears their session, then sends them home
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("index")


# this is the shared forgot password brain, it finds the right user and emails them a reset link
def _forgot_password_request(request, portal_role, css_file, login_url_name, sent_url_name):
    context = {
        "css_file": css_file,
        "login_url_name": login_url_name,
        "portal_label": portal_role.capitalize(),
    }
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        try:
            user = User.objects.get(email__iexact=email, profile__role=portal_role)
            if user.is_active:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    f"/reset-password/{uid}/{token}/"
                )
                subject = "NeuroNest - Reset your password"
                body = (
                    f"Hi {user.profile.full_name or user.username},\n\n"
                    f"A password reset was requested for your NeuroNest {portal_role} account.\n\n"
                    f"Click the link below to set a new password (valid for 24 hours):\n"
                    f"{reset_url}\n\n"
                    f"If you did not request this, you can safely ignore this email.\n\n"
                    f"- The NeuroNest Team"
                )
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        except (User.DoesNotExist, AttributeError):
            pass  # never reveal whether the email exists
        return redirect(sent_url_name)
    return render(request, "accounts/forgot-password.html", context)


# this shows the check your email page after a reset link was sent
def _password_reset_sent(request, css_file, login_url_name, portal_label):
    return render(request, "accounts/password-reset-sent.html", {
        "css_file": css_file,
        "login_url_name": login_url_name,
        "portal_label": portal_label,
    })


# this connects the admin forgot password page to the shared forgot password brain
def portaladmin_forgot_password(request):
    return _forgot_password_request(
        request,
        portal_role="admin",
        css_file="css/employee.css",
        login_url_name="portaladmin_login",
        sent_url_name="portaladmin_password_reset_sent",
    )


# this shows the admin their reset link sent confirmation page
def portaladmin_password_reset_sent(request):
    return _password_reset_sent(request, "css/employee.css", "portaladmin_login", "Admin")


# this connects the employee forgot password page to the shared forgot password brain
def employee_forgot_password(request):
    return _forgot_password_request(
        request,
        portal_role="employee",
        css_file="css/employee.css",
        login_url_name="employee_login",
        sent_url_name="employee_password_reset_sent",
    )


# this shows the employee their reset link sent confirmation page
def employee_password_reset_sent(request):
    return _password_reset_sent(request, "css/employee.css", "employee_login", "Employee")


# this connects the patient forgot password page to the shared forgot password brain
def patient_forgot_password(request):
    return _forgot_password_request(
        request,
        portal_role="patient",
        css_file="css/patient.css",
        login_url_name="patient_login",
        sent_url_name="patient_password_reset_sent",
    )


# this shows the patient their reset link sent confirmation page
def patient_password_reset_sent(request):
    return _password_reset_sent(request, "css/patient.css", "patient_login", "Patient")


# this is where the reset email link lands, it checks the token and lets the user type a new password
def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    token_valid = user is not None and default_token_generator.check_token(user, token)

    if not token_valid:
        return render(request, "accounts/reset-password-invalid.html")

    if request.method == "POST":
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        else:
            user.set_password(password1)
            user.save()
            return redirect("password_reset_done")

    return render(request, "accounts/reset-password.html", {
        "uidb64": uidb64,
        "token": token,
    })


# this shows the all done page after the password was changed
def password_reset_done(request):
    return render(request, "accounts/password-reset-done.html")
