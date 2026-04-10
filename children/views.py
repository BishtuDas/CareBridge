from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ChildForm
from .models import Child


@login_required
def child_list(request):
    children = Child.objects.filter(parent=request.user)
    return render(request, "children/list.html", {"children": children})


@login_required
def add_child(request):
    if request.method == "POST":
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = request.user
            child.save()
            return redirect("child_list")
    else:
        form = ChildForm()

    return render(request, "children/add.html", {"form": form})


@login_required
def edit_child(request, child_id):
    child = get_object_or_404(Child, id=child_id, parent=request.user)

    if request.method == "POST":
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            return redirect("child_list")
    else:
        form = ChildForm(instance=child)

    return render(request, "children/edit.html", {"form": form, "child": child})
