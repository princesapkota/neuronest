from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from .models import DiagnosticResult
from .forms import DiagnosticUploadForm
from notifications.models import Notification

from .pneumonia_integration import build_pneumonia_report_png
from .fracture_integration import build_fracture_report_png
from .tumor_integration import build_tumor_report_png

# we reuse the same role checker that lives in accounts so we don't write the same thing twice
from accounts.views import _require_role

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


# this grabs the saved result image from the database and sends it back as a viewable PNG
def diagnostic_output_png(request, result_id: int):
    result = get_object_or_404(DiagnosticResult, id=result_id)

    if not result.output_png:
        raise Http404("No output PNG available yet.")

    resp = HttpResponse(
        result.output_png,
        content_type=result.output_png_content_type or "image/png"
    )
    resp["Content-Disposition"] = f'inline; filename="{result.output_png_name or "result.png"}"'
    return resp


# this is the page where an employee uploads a scan, then we run the right AI model on it
@login_required
def employee_upload(request):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    if request.method == "POST":
        form = DiagnosticUploadForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.cleaned_data["patient"]
            model_type = form.cleaned_data["model_type"]
            input_file = form.cleaned_data["input_file"]

            result = DiagnosticResult.objects.create(
                patient=patient,
                employee=request.user.profile,
                model_type=model_type,
                input_file=input_file,
                status=DiagnosticResult.Status.DRAFT,
            )

            # Pneumonia integration
            if result.model_type == DiagnosticResult.ModelType.PNEUMONIA and result.input_file:
                png_bytes, _pred = build_pneumonia_report_png(result.input_file.path)
                result.set_output_png(png_bytes, filename=f"pneumonia_report_{result.id}.png")
                result.save()

            # Fracture integration
            elif result.model_type == DiagnosticResult.ModelType.FRACTURE and result.input_file:
                png_bytes, _pred = build_fracture_report_png(result.input_file.path)
                result.set_output_png(png_bytes, filename=f"fracture_report_{result.id}.png")
                result.save()

            # Brain tumor integration
            elif result.model_type == DiagnosticResult.ModelType.BRAIN_TUMOR and result.input_file:
                png_bytes, _pred = build_tumor_report_png(result.input_file.path)
                result.set_output_png(png_bytes, filename=f"tumor_report_{result.id}.png")
                result.save()

            return redirect("diagnostics:employee_result_review", result_id=result.id)
    else:
        form = DiagnosticUploadForm()

    return render(request, "employee/diagnostics-upload.html", {"form": form})


# this shows one finished result to the employee who made it
@login_required
def employee_result_detail(request, result_id: int):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    result = get_object_or_404(
        DiagnosticResult,
        id=result_id,
        employee=request.user.profile,
    )

    return render(request, "employee/result-detail.html", {"result": result})


# this is the review screen where the employee decides to forward or reject the report
@login_required
def employee_result_review(request, result_id: int):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    result = get_object_or_404(
        DiagnosticResult,
        id=result_id,
        employee=request.user.profile,
    )

    return render(request, "employee/result-review.html", {"result": result})


# this marks a report as rejected so it never reaches the patient
@login_required
def reject_report(request, result_id: int):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    if request.method != "POST":
        return redirect("diagnostics:employee_result_review", result_id=result_id)

    result = get_object_or_404(
        DiagnosticResult,
        id=result_id,
        employee=request.user.profile,
    )

    result.status = DiagnosticResult.Status.REJECTED
    result.save(update_fields=["status"])

    return redirect("employee_dashboard")


# this sends the approved report to the patient and drops them a notification about it
@login_required
def forward_report_to_patient(request, result_id: int):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    if request.method != "POST":
        return redirect("diagnostics:employee_result_review", result_id=result_id)

    result = get_object_or_404(
        DiagnosticResult,
        id=result_id,
        employee=request.user.profile,
    )

    if result.status != DiagnosticResult.Status.FORWARDED:
        result.status = DiagnosticResult.Status.FORWARDED
        result.save(update_fields=["status"])

        Notification.objects.create(
            patient=result.patient,
            result=result,
            title="Diagnostic Report Available",
            message=(
                f"Your {result.get_model_type_display()} report is now available."
            ),
        )

    return redirect("diagnostics:employee_reports")


# this lists every report the logged in employee has worked on
@login_required
def employee_reports(request):
    if not _require_role(request.user, "employee"):
        return redirect("index")

    results = DiagnosticResult.objects.filter(
        employee=request.user.profile
    ).order_by("-created_at")

    return render(request, "employee/reports.html", {"results": results})


# this builds a downloadable PDF version of the report with all the details and the image
def diagnostic_output_pdf(request, result_id: int):
    result = get_object_or_404(DiagnosticResult, id=result_id)

    if not result.output_png:
        raise Http404("No output PNG available.")

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    # Title
    elements.append(Paragraph("NeuroNest Diagnostic Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Basic Info
    elements.append(Paragraph(f"Model: {result.get_model_type_display()}", styles["Normal"]))
    elements.append(Paragraph(f"Date: {result.created_at}", styles["Normal"]))

    if result.verdict:
        elements.append(Paragraph(f"Verdict: {result.get_verdict_display()}", styles["Normal"]))

    elements.append(Paragraph(f"Status: {result.get_status_display()}", styles["Normal"]))

    if result.employee:
        elements.append(Paragraph(f"Reviewed By: {result.employee.full_name}", styles["Normal"]))

    elements.append(Spacer(1, 16))

    # Convert PNG bytes to image
    img_buffer = BytesIO(result.output_png)
    img = RLImage(img_buffer, width=400, height=400)

    elements.append(img)

    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph(
        "This report is generated by NeuroNest (Academic Prototype). Not for clinical use.",
        styles["Italic"]
    ))

    doc.build(elements)

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="NeuroNest_Report_{result.id}.pdf"'

    return response
