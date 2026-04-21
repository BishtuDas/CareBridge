from django import forms

from children.models import Child
from users.models import User


class ChatStartForm(forms.Form):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role="doctor"), empty_label="Select doctor"
    )
    child = forms.ModelChoiceField(queryset=Child.objects.none())

    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(*args, **kwargs)
        if parent is not None:
            self.fields["child"].queryset = Child.objects.filter(parent=parent)


class MessageForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
