from django.urls import path
from accounts import views
from accounts import auth_views
from accounts import admin_ui_views

# this list connects each web address to the backend function that should run for it
urlpatterns = [
    # Landing page
    path("", views.index, name="index"),

    # Patient signup + verify
    path("patient/signup/", views.patient_signup, name="patient_signup"),
    path("verify/sent/", views.verify_email_sent, name="verify_email_sent"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("portaladmin/dashboard/", admin_ui_views.admin_dashboard, name="portaladmin_dashboard"),

    # these connect each login page and its forgot password pages to the backend
    path("portaladmin/login/", auth_views.portaladmin_login_view, name="portaladmin_login"),
    path("portaladmin/forgot-password/", auth_views.portaladmin_forgot_password, name="portaladmin_forgot_password"),
    path("portaladmin/forgot-password/sent/", auth_views.portaladmin_password_reset_sent, name="portaladmin_password_reset_sent"),
    path("employee/login/", auth_views.employee_login_view, name="employee_login"),
    path("employee/forgot-password/", auth_views.employee_forgot_password, name="employee_forgot_password"),
    path("employee/forgot-password/sent/", auth_views.employee_password_reset_sent, name="employee_password_reset_sent"),
    path("employee/dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("patient/login/", auth_views.patient_login_view, name="patient_login"),
    path("patient/forgot-password/", auth_views.patient_forgot_password, name="patient_forgot_password"),
    path("patient/forgot-password/sent/", auth_views.patient_password_reset_sent, name="patient_password_reset_sent"),
    # these two are the shared reset link pages that any role uses after clicking the email link
    path("reset-password/<uidb64>/<token>/", auth_views.password_reset_confirm, name="password_reset_confirm"),
    path("reset-password/done/", auth_views.password_reset_done, name="password_reset_done"),

    # Logout
    path("logout/", auth_views.logout_view, name="logout"),

    # Patient pages
    path("patient/dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("patient/results/", views.patient_results, name="patient_results"),
    path("patient/notifications/", views.patient_notifications, name="patient_notifications"),

    # Admin pages
    path("portaladmin/employees/", admin_ui_views.employees_list, name="employees_list"),
    path("portaladmin/employees/create/", admin_ui_views.create_employee, name="create_employee"),
    path("portaladmin/employees/<int:profile_id>/delete/", admin_ui_views.delete_employee, name="delete_employee"),
    path("portaladmin/patients/", admin_ui_views.patients_list, name="patients_list"),
    path("portaladmin/patients/<int:profile_id>/delete/", admin_ui_views.delete_patient, name="delete_patient"),
    path("patient/results/<int:result_id>/", views.patient_result_detail, name="patient_result_detail"),
]