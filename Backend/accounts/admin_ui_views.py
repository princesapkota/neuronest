from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.conf import settings

from accounts.models import Profile


def _is_portal_admin(request) -> bool:
    try:
        return request.user.is_authenticated and request.user.profile.role == "admin"
    except Exception:
        return False


@login_required
def create_employee(request):
    if not _is_portal_admin(request):
        return redirect("index")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        personal_email = request.POST.get("personal_email", "").strip().lower()
        assigned_email = request.POST.get("assigned_email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([full_name, personal_email, assigned_email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, "admin_ui/admin-create-employee.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "admin_ui/admin-create-employee.html")

        # ✅ Use assigned_email as username (easy login)
        username = assigned_email

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "An employee with this assigned email already exists.")
            return render(request, "admin_ui/admin-create-employee.html")

        if User.objects.filter(email__iexact=assigned_email).exists():
            messages.error(request, "Assigned email is already in use.")
            return render(request, "admin_ui/admin-create-employee.html")

        # Create Django User (assigned email used for login)
        user = User.objects.create_user(
            username=username,
            email=assigned_email,
            password=password,
        )
        user.is_active = True
        user.save()

        # ✅ Create Profile explicitly (because role/full_name are required)
        Profile.objects.create(
            user=user,
            role="employee",
            full_name=full_name,
            personal_email=personal_email,
        )

        # Email credentials to personal email
        login_url = "http://127.0.0.1:8000/employee/login/"
        subject = "NeuroNest Employee Account Credentials"
        body = (
            f"Hello {full_name},\n\n"
            f"Your NeuroNest employee account has been created.\n\n"
            f"Assigned login email: {assigned_email}\n"
            f"Password: {password}\n\n"
            f"Login here: {login_url}\n\n"
            f"- NeuroNest"
        )

        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [personal_email], fail_silently=False)
        except Exception as e:
            messages.warning(request, f"Employee created, but email failed to send: {e}")
            return redirect("employees_list")

        messages.success(request, "Employee created and credentials emailed successfully.")
        return redirect("employees_list")

    return render(request, "admin_ui/admin-create-employee.html")
@login_required
def employees_list(request):
    if not _is_portal_admin(request):
        return redirect("index")

    employees = Profile.objects.select_related("user").filter(role="employee").order_by("-created_at")
    return render(request, "admin_ui/admin-employees.html", {"employees": employees})