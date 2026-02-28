from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages


def _role_login(request, template_name: str, required_role: str, success_url_name: str):
    """
    Shared role-based login handler for portaladmin/employee/patient.

    Fixes the common issue:
    - If a user is already logged in as Django admin (superuser/staff),
      it will log them out and reload the portal login page instead of bouncing to landing.
    """

    # If already authenticated, route them properly (or reset session if superuser/staff)
    if request.user.is_authenticated:

        # ✅ If they are logged into Django admin (superuser/staff),
        # don't block portal login. Reset session and reload this page.
        if request.user.is_superuser or request.user.is_staff:
            logout(request)
            return redirect(request.path)

        # Normal role-based redirects
        try:
            role = request.user.profile.role
            if role == "admin":
                return redirect("portaladmin_dashboard")
            if role == "employee":
                return redirect("employee_dashboard")
            if role == "patient":
                return redirect("patient_dashboard")
        except Exception:
            # Profile missing or role not set -> reset + go home
            logout(request)
            return redirect("index")

    # Handle POST login
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Try username login first
        user = authenticate(request, username=identifier, password=password)

        # Try email login if username fails
        if user is None:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            messages.error(request, "Invalid credentials.")
            return render(request, template_name)

        if not user.is_active:
            messages.error(request, "Account inactive. Please verify email or contact admin.")
            return render(request, template_name)

        # ✅ Block superuser/staff from logging into app portals
        # (they should use Django /admin/)
        if user.is_superuser or user.is_staff:
            messages.error(request, "Please use the Django Admin (/admin/) to log in as superuser.")
            return render(request, template_name)

        # Role check
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

    # GET request
    return render(request, template_name)


def portaladmin_login_view(request):
    return _role_login(
        request=request,
        template_name="admin_ui/admin-login.html",
        required_role="admin",
        success_url_name="portaladmin_dashboard",
    )


def employee_login_view(request):
    return _role_login(
        request=request,
        template_name="employee/employee-login.html",
        required_role="employee",
        success_url_name="employee_dashboard",
    )


def patient_login_view(request):
    return _role_login(
        request=request,
        template_name="patient/patient-login.html",
        required_role="patient",
        success_url_name="patient_dashboard",
    )


def logout_view(request):
    logout(request)
    return redirect("index")