from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def _require_role(user, role: str):
    return hasattr(user, "profile") and user.profile.role == role


@login_required
def admin_dashboard(request):
    if not _require_role(request.user, "admin"):
        return redirect("portaladmin_login")
    return render(request, "admin_ui/admin-dashboard.html")


@login_required
def employee_dashboard(request):
    if not _require_role(request.user, "employee"):
        return redirect("employee_login")
    return render(request, "employee/dashboard.html")


@login_required
def patient_dashboard(request):
    if not _require_role(request.user, "patient"):
        return redirect("patient_login")
    return render(request, "patient/patient-dashboard.html")


@login_required
def patient_results(request):
    if not _require_role(request.user, "patient"):
        return redirect("patient_login")
    return render(request, "patient/results.html")


@login_required
def patient_notifications(request):
    if not _require_role(request.user, "patient"):
        return redirect("patient_login")
    return render(request, "patient/notifications.html")