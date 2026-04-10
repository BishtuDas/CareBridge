from django import forms

from .models import Report


class ReportUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("child", "file")

    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(*args, **kwargs)
        if parent is not None:
            self.fields["child"].queryset = self.fields["child"].queryset.filter(
                parent=parent
            )
