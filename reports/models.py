from django.db import models


class Report(models.Model):
    child = models.ForeignKey(
        "children.Child", on_delete=models.CASCADE, related_name="reports"
    )
    file = models.FileField(upload_to="reports/")
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"Report for {self.child.name}"