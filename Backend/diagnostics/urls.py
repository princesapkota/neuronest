from django.urls import path
from . import views

app_name = "diagnostics"

# this list connects each diagnostics web address to the backend function that should run for it
urlpatterns = [
    # upload + reports
    path("employee/upload/", views.employee_upload, name="employee_upload"),
    path("employee/reports/", views.employee_reports, name="employee_reports"),

    # detail + review
    path("employee/result/<int:result_id>/detail/", views.employee_result_detail, name="employee_result_detail"),
    path("employee/result/<int:result_id>/", views.employee_result_review, name="employee_result_review"),
    path("employee/result/<int:result_id>/reject/", views.reject_report, name="reject_report"),
    path("employee/result/<int:result_id>/forward/", views.forward_report_to_patient, name="forward_report_to_patient"),

    # serve output PNG stored in DB
    path("output/<int:result_id>/pdf/", views.diagnostic_output_pdf, name="diagnostic_output_pdf"),
    path("output/<int:result_id>/png/", views.diagnostic_output_png, name="diagnostic_output_png")
]