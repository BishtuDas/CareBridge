from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from children.models import Child
from chat.models import Chat

@login_required
def dashboard(request):
    # Revert to standard role-based logic
    role = getattr(request.user, 'role', 'parent')

    if role == "doctor":
        chats = Chat.objects.filter(doctor=request.user).order_by("-id")[:5]
        return render(request, "doctor/dashboard.html", {"chats": chats})
    else:
        children = Child.objects.filter(parent=request.user)
        chats = Chat.objects.filter(parent=request.user).order_by("-id")[:3]
        return render(
            request, "patient/dashboard.html", {"children": children, "chats": chats}
        )

@login_required
def logout_user(request):
    logout(request)
    return redirect("/login/")
