from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm


@login_required
def profile_view(request):
    base_template = (
        "base_doctor.html" if request.user.role == "doctor" else "base_patient.html"
    )

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user, user=request.user)

    return render(
        request,
        "users/profile.html",
        {"form": form, "base_template": base_template},
    )
