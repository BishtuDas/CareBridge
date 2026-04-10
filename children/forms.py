from django import forms

from .models import Child


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ["name", "age", "gender", "notes"]
