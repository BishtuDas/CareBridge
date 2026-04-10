from django.urls import path

from .views import doctor_report_list, upload_report

urlpatterns = [
    path("report/upload/", upload_report, name="upload_report"),
    path("doctor/reports/", doctor_report_list, name="doctor_report_list"),
]
