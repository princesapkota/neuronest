from django.urls import path
from accounts import views
from accounts import auth_views
from accounts import portalviews
from accounts import admin_ui_views

urlpatterns = [
    # Landing page
    path("", views.index, name="index"),

    # Patient signup + verify
    path("patient/signup/", views.patient_signup, name="patient_signup"),
    path("verify/sent/", views.verify_email_sent, name="verify_email_sent"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),

    # Login routes
    path("portaladmin/login/", auth_views.portaladmin_login_view, name="portaladmin_login"),
    path("employee/login/", auth_views.employee_login_view, name="employee_login"),
    path("patient/login/", auth_views.patient_login_view, name="patient_login"),

    # Logout
    path("logout/", auth_views.logout_view, name="logout"),

    # Dashboards
    path("portaladmin/dashboard/", portalviews.admin_dashboard, name="portaladmin_dashboard"),
    path("employee/dashboard/", portalviews.employee_dashboard, name="employee_dashboard"),
    path("patient/dashboard/", portalviews.patient_dashboard, name="patient_dashboard"),

    # Patient pages
    path("patient/results/", portalviews.patient_results, name="patient_results"),
    path("patient/notifications/", portalviews.patient_notifications, name="patient_notifications"),

    # Admin employee management
    path("portaladmin/employees/", admin_ui_views.employees_list, name="employees_list"),
    path("portaladmin/employees/create/", admin_ui_views.create_employee, name="create_employee"),
]