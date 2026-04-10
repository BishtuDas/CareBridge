from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai import suggest_reply
from .forms import ChatStartForm, MessageForm
from .models import Chat, Message
from reports.models import Report


@login_required
def chat_list(request):
    if request.user.role == "parent":
        chats = Chat.objects.filter(parent=request.user).order_by("-id")
    elif request.user.role == "doctor":
        chats = Chat.objects.filter(doctor=request.user).order_by("-id")
    else:
        return HttpResponse("Unauthorized", status=403)

    template = (
        "chat/chat_list_patient.html"
        if request.user.role == "parent"
        else "chat/chat_list_doctor.html"
    )
    return render(request, template, {"chats": chats})



@login_required
def start_chat(request):
    if request.user.role != "parent":
        return HttpResponse("Unauthorized", status=403)

    report_id = request.GET.get("report")
    report = None
    if report_id:
        report = Report.objects.filter(
            id=report_id, child__parent=request.user
        ).first()

    initial = {"child": report.child.id} if report else None

    if request.method == "POST":
        form = ChatStartForm(request.POST, parent=request.user)
        if form.is_valid():
            doctor = form.cleaned_data["doctor"]
            child = form.cleaned_data["child"]
            report_id = request.POST.get("report_id")
            report = None
            if report_id:
                report = Report.objects.filter(
                    id=report_id, child=child, child__parent=request.user
                ).first()
            chat, created = Chat.objects.get_or_create(
                parent=request.user, doctor=doctor, child=child
            )
            if created:
                initial_message = "Hi doctor, please review my child's report."
                if report and report.summary:
                    initial_message = (
                        f"{initial_message} Summary: {report.summary}"
                    )
                elif report:
                    initial_message = f"{initial_message} Report uploaded."
                Message.objects.create(
                    chat=chat,
                    sender=request.user,
                    text=initial_message,
                )
            return redirect("chat_detail", chat_id=chat.id)
    else:
        form = ChatStartForm(parent=request.user, initial=initial)

    return render(
        request,
        "chat/chat_start.html",
        {"form": form, "report": report},
    )


@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)

    if request.user.role == "parent" and chat.parent != request.user:
        return HttpResponse("Unauthorized", status=403)
    if request.user.role == "doctor" and chat.doctor != request.user:
        return HttpResponse("Unauthorized", status=403)
    if request.user.role not in ("parent", "doctor"):
        return HttpResponse("Unauthorized", status=403)

    messages = Message.objects.filter(chat=chat).order_by("created_at")
    reports = chat.child.reports.order_by("-id") if chat.child else []

    suggestion = ""
    if request.user.role == "doctor":
        report_summaries = "\n".join(
            report.summary for report in reports if report.summary
        )
        last_message = messages.last().text if messages.exists() else ""
        suggestion = suggest_reply(report_summaries, last_message)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                chat=chat,
                sender=request.user,
                text=form.cleaned_data["text"],
            )
            return redirect("chat_detail", chat_id=chat.id)
    else:
        form = MessageForm()

    template = (
        "chat/chat_detail_patient.html"
        if request.user.role == "parent"
        else "chat/chat_detail_doctor.html"
    )
    return render(
        request,
        template,
        {
            "chat": chat,
            "messages": messages,
            "form": form,
            "reports": reports,
            "suggestion": suggestion,
        },
    )



@login_required
def fetch_messages(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)

    if request.user not in (chat.parent, chat.doctor):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    messages = Message.objects.filter(chat=chat).order_by("created_at")

    data = [
        {
            "sender": m.sender.username,
            "text": m.text,
            "is_me": m.sender == request.user,
        }
        for m in messages
    ]

    return JsonResponse({"messages": data})
