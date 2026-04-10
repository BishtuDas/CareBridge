from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from .ai import summarize_text
from .forms import ReportUploadForm
from .models import Report
from .utils import extract_text


@login_required
def upload_report(request):
    if request.user.role != "parent":
        return HttpResponse("Unauthorized", status=403)

    child_id = request.GET.get("child")
    initial = {"child": child_id} if child_id else None

    if request.method == "POST":
        form = ReportUploadForm(request.POST, request.FILES, parent=request.user)
        if form.is_valid():
            report = form.save()
            extracted = extract_text(report.file.path)
            report.extracted_text = extracted or ""
            summary = summarize_text(report.extracted_text)
            report.summary = summary if summary else "Could not generate summary."
            report.save()
            return render(request, "reports/upload_result.html", {"report": report})
    else:
        form = ReportUploadForm(parent=request.user, initial=initial)

    reports = Report.objects.filter(child__parent=request.user).order_by("-id")

    return render(
        request,
        "reports/upload.html",
        {"form": form, "reports": reports},
    )


@login_required
def doctor_report_list(request):
    if request.user.role != "doctor":
        return HttpResponse("Unauthorized", status=403)

    reports = (
        Report.objects.select_related("child", "child__parent")
        .order_by("-id")
    )

    return render(
        request,
        "reports/doctor_report_list.html",
        {"reports": reports},
    )
