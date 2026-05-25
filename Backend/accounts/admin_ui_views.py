from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.models import Profile, Role
# reuse the shared role checker instead of writing the admin check logic again
from accounts.views import _require_role


# this is a quick yes/no check that the person using the page is actually a logged in admin
def _is_portal_admin(request) -> bool:
    return request.user.is_authenticated and _require_role(request.user, Role.ADMIN)


# this loads the admin home dashboard (only admins are let in)
@login_required
def admin_dashboard(request):
    if not _is_portal_admin(request):
        return redirect("index")

    return render(request, "admin_ui/admin-dashboard.html")


# this is the form where an admin makes a new employee account and emails them the login details
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

        username = assigned_email

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "An employee with this assigned email already exists.")
            return render(request, "admin_ui/admin-create-employee.html")

        if User.objects.filter(email__iexact=assigned_email).exists():
            messages.error(request, "Assigned email is already in use.")
            return render(request, "admin_ui/admin-create-employee.html")

        user = User.objects.create_user(
            username=username,
            email=assigned_email,
            password=password,
        )
        user.is_active = True
        user.save()

        Profile.objects.update_or_create(
            user=user,
            defaults={
                "role": Role.EMPLOYEE,
                "full_name": full_name,
                "personal_email": personal_email,
            },
        )

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
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [personal_email],
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(request, f"Employee created, but email failed to send: {e}")
            return redirect("employees_list")

        messages.success(request, "Employee created and credentials emailed successfully.")
        return redirect("employees_list")

    return render(request, "admin_ui/admin-create-employee.html")


# this shows the admin a list of every employee account that exists
@login_required
def employees_list(request):
    if not _is_portal_admin(request):
        return redirect("index")

    query = request.GET.get("q", "").strip()
    employees = Profile.objects.select_related("user").filter(role=Role.EMPLOYEE)
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) | Q(user__email__icontains=query)
        )
    employees = employees.order_by("-created_at")

    return render(request, "admin_ui/admin-employees.html", {"employees": employees, "query": query})


@login_required
@require_POST
def delete_employee(request, profile_id):
    if not _is_portal_admin(request):
        return redirect("index")

    profile = get_object_or_404(Profile, id=profile_id, role=Role.EMPLOYEE)
    profile.user.delete()
    messages.success(request, "Employee deleted successfully.")
    return redirect("employees_list")


# this shows the admin a list of every patient account that exists
@login_required
def patients_list(request):
    if not _is_portal_admin(request):
        return redirect("index")

    query = request.GET.get("q", "").strip()
    patients = Profile.objects.select_related("user").filter(role=Role.PATIENT)
    if query:
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(hospital_patient_id__icontains=query)
        )
    patients = patients.order_by("-created_at")

    return render(request, "admin_ui/admin-patients.html", {"patients": patients, "query": query})


@login_required
@require_POST
def delete_patient(request, profile_id):
    if not _is_portal_admin(request):
        return redirect("index")

    profile = get_object_or_404(Profile, id=profile_id, role=Role.PATIENT)
    profile.user.delete()
    messages.success(request, "Patient deleted successfully.")
    return redirect("patients_list")