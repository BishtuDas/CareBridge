from django.contrib.auth.decorators import login_required
import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai import (
    _clean_chat_reply,
    answer_from_reports,
    build_patient_problem_and_reply,
    suggest_reply,
)
from .forms import ChatStartForm, MessageForm
from .models import AIDraftReply, Chat, DoctorAIResponse, DoctorNote, Message
from reports.models import Report
from reports.ai import summarize_text
from reports.utils import extract_text


DOCTOR_NOTE_TEMPLATE_DEFAULTS = {
    DoctorNote.TEMPLATE_INITIAL_ASSESSMENT: {
        "chief_complaint": "Parent reports:",
        "clinical_observations": "Key observations from history/reports:",
        "assessment": "Initial clinical impression:",
        "plan": "Immediate plan:",
        "follow_up_instructions": "Follow-up in ____ days or sooner if symptoms worsen.",
    },
    DoctorNote.TEMPLATE_FOLLOW_UP: {
        "chief_complaint": "Progress update since last consult:",
        "clinical_observations": "Current findings:",
        "assessment": "Response to treatment:",
        "plan": "Continue/adjust management:",
        "follow_up_instructions": "Next follow-up on ____ / Red flags shared with guardian.",
    },
    DoctorNote.TEMPLATE_DIAGNOSIS: {
        "chief_complaint": "Presenting concern:",
        "clinical_observations": "Diagnostic evidence:",
        "assessment": "Working diagnosis:",
        "plan": "Treatment and monitoring plan:",
        "follow_up_instructions": "Reassessment criteria and timeline:",
    },
}


def _append_problem_json_file(chat_id, payload):
    target_dir = Path(settings.MEDIA_ROOT) / "ai_chat_logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"chat_{chat_id}.json"

    existing = []
    if target_file.exists():
        try:
            existing = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    existing.append(payload)
    target_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _attachment_is_report_like(file_name):
    suffix = Path(file_name or "").suffix.lower()
    return suffix in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _summarize_chat_attachment(message):
    if not message.attachment:
        return ""

    if not _attachment_is_report_like(message.attachment.name):
        return ""

    try:
        extracted = extract_text(message.attachment.path)
    except Exception:
        extracted = ""

    if not extracted:
        return ""

    summary = summarize_text(extracted)
    return summary or ""


def _create_ai_draft_for_parent_message(chat, source_message):
    reports = chat.child.reports.order_by("-id") if chat.child else []
    report_summaries = "\n".join(
        report.summary for report in reports if report.summary
    )
    report_texts = "\n".join(
        report.extracted_text for report in reports if report.extracted_text
    )

    patient_name = ""
    if chat.child and chat.child.name:
        patient_name = chat.child.name
    elif chat.parent and chat.parent.username:
        patient_name = chat.parent.username

    ai_payload = build_patient_problem_and_reply(
        report_summaries,
        report_texts,
        source_message.text,
        patient_name,
    )
    if not ai_payload:
        return

    draft = AIDraftReply.objects.create(
        chat=chat,
        source_message=source_message,
        doctor=chat.doctor,
        parent=chat.parent,
        child=chat.child,
        patient_problem_json={
            "message": source_message.text,
            "analysis": {
                "concern_summary": ai_payload.get("concern_summary", ""),
                "urgency": ai_payload.get("urgency", "low"),
                "symptoms": ai_payload.get("symptoms", []),
                "recommended_next_step": ai_payload.get("recommended_next_step", ""),
            },
            "reply_options": ai_payload.get("reply_options", []),
        },
        generated_reply=_clean_chat_reply(ai_payload.get("doctor_draft_reply", "")),
        status=AIDraftReply.STATUS_PENDING,
    )

    _append_problem_json_file(
        chat.id,
        {
            "source_message_id": source_message.id,
            "patient_message": source_message.text,
            "analysis": draft.patient_problem_json.get("analysis", {}),
            "generated_reply": draft.generated_reply,
            "status": draft.status,
            "created_at": draft.created_at.isoformat(),
        },
    )

    # Keep AI replies as doctor-side suggestions only.
    # A message is sent to patient only after explicit doctor action.


def _build_attachment_message_text(file_name):
    return f"Shared a file: {Path(file_name).name}"


def _serialize_doctor_note(note):
    return {
        "id": note.id,
        "template_type": note.template_type,
        "chief_complaint": note.chief_complaint,
        "clinical_observations": note.clinical_observations,
        "assessment": note.assessment,
        "plan": note.plan,
        "follow_up_instructions": note.follow_up_instructions,
        "is_finalized": note.is_finalized,
        "updated_at": note.updated_at.isoformat(),
    }


def _note_snapshot_for_child_record(note):
    return (
        f"[Doctor Note | {note.get_template_type_display()}]\n"
        f"Chief Complaint: {note.chief_complaint}\n"
        f"Clinical Observations: {note.clinical_observations}\n"
        f"Assessment: {note.assessment}\n"
        f"Plan: {note.plan}\n"
        f"Follow-up: {note.follow_up_instructions}"
    ).strip()


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
    ai_responses = []
    pending_ai_drafts = []
    if request.user.role == "doctor":
        report_summaries = "\n".join(
            report.summary for report in reports if report.summary
        )
        last_message = messages.last().text if messages.exists() else ""
        suggestion = suggest_reply(report_summaries, last_message)
        ai_responses = chat.ai_responses.order_by("created_at")
        pending_ai_drafts = chat.ai_draft_replies.filter(
            status=AIDraftReply.STATUS_PENDING
        ).order_by("-id")

    if request.method == "POST":
        form = MessageForm(request.POST)
        attachment = request.FILES.get("attachment")
        text = (request.POST.get("text") or "").strip()
        if form.is_valid() and (text or attachment):
            created_message = Message.objects.create(
                chat=chat,
                sender=request.user,
                text=text or _build_attachment_message_text(attachment.name if attachment else ""),
                attachment=attachment,
            )

            attachment_summary = _summarize_chat_attachment(created_message)
            if attachment_summary:
                created_message.ai_generation_note = attachment_summary
                created_message.save(update_fields=["ai_generation_note"])

            if request.user.role == "parent":
                _create_ai_draft_for_parent_message(chat, created_message)
            return redirect("chat_detail", chat_id=chat.id)
        form.add_error(None, "Please type a message or choose a file to share.")
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
            "ai_responses": ai_responses,
            "pending_ai_drafts": pending_ai_drafts,
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
            "id": m.id,
            "sender": m.sender.username,
            "text": m.text,
            "is_me": m.sender == request.user,
            "is_ai_generated": m.is_ai_generated,
            "ai_generation_note": m.ai_generation_note,
            "sender_role": m.sender.role,
            "attachment_url": m.attachment.url if m.attachment else "",
            "attachment_name": Path(m.attachment.name).name if m.attachment else "",
        }
        for m in messages
    ]

    pending_ai_drafts = []
    if request.user.role == "doctor" and chat.doctor == request.user:
        drafts = chat.ai_draft_replies.filter(status=AIDraftReply.STATUS_PENDING).order_by("id")
        pending_ai_drafts = [
            {
                "id": d.id,
                "generated_reply": _clean_chat_reply(d.generated_reply),
                "reply_options": (d.patient_problem_json or {}).get("reply_options", []),
                "concern_summary": ((d.patient_problem_json or {}).get("analysis", {}) or {}).get("concern_summary", ""),
                "urgency": ((d.patient_problem_json or {}).get("analysis", {}) or {}).get("urgency", "low"),
            }
            for d in drafts
        ]

    return JsonResponse({"messages": data, "pending_ai_drafts": pending_ai_drafts})


@login_required
def doctor_ai_help(request, chat_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    chat = get_object_or_404(Chat, id=chat_id)
    if request.user.role != "doctor" or chat.doctor != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    question = (payload.get("question") or "").strip()
    if not question:
        return JsonResponse({"answer": "Please enter a question."})

    reports = chat.child.reports.order_by("-id") if chat.child else []
    report_summaries = "\n".join(
        report.summary for report in reports if report.summary
    )
    report_texts = "\n".join(
        report.extracted_text for report in reports if report.extracted_text
    )

    answer = answer_from_reports(report_summaries, report_texts, question)
    if not answer:
        answer = "I do not have that information from the uploaded reports."

    if chat.child:
        DoctorAIResponse.objects.create(
            chat=chat,
            doctor=chat.doctor,
            parent=chat.parent,
            child=chat.child,
            question=question,
            answer=answer,
        )

    return JsonResponse({"answer": answer})


@login_required
def doctor_ai_draft_action(request, chat_id, draft_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    chat = get_object_or_404(Chat, id=chat_id)
    if request.user.role != "doctor" or chat.doctor != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    draft = get_object_or_404(AIDraftReply, id=draft_id, chat=chat)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    action = (payload.get("action") or "").strip().lower()
    edited_text = (payload.get("edited_text") or "").strip()
    removal_reason = (payload.get("removal_reason") or "").strip()

    if action == "send":
        text_to_send = edited_text or draft.generated_reply
        if not text_to_send:
            return JsonResponse({"error": "Reply text is empty."}, status=400)

        Message.objects.create(
            chat=chat,
            sender=chat.doctor,
            text=text_to_send,
            is_ai_generated=True,
            ai_generation_note="Sent from AI draft by doctor.",
        )
        draft.edited_reply = edited_text
        draft.status = (
            AIDraftReply.STATUS_EDITED_SENT if edited_text else AIDraftReply.STATUS_SENT
        )
        draft.save(update_fields=["edited_reply", "status", "updated_at"])

        _append_problem_json_file(
            chat.id,
            {
                "source_message_id": draft.source_message_id,
                "action": "send",
                "used_reply": text_to_send,
                "status": draft.status,
            },
        )
        return JsonResponse({"ok": True})

    if action == "remove":
        if not removal_reason:
            return JsonResponse({"error": "Removal reason is required."}, status=400)
        draft.removal_reason = removal_reason
        draft.status = AIDraftReply.STATUS_REMOVED
        draft.save(update_fields=["removal_reason", "status", "updated_at"])

        _append_problem_json_file(
            chat.id,
            {
                "source_message_id": draft.source_message_id,
                "action": "remove",
                "removal_reason": removal_reason,
                "status": draft.status,
            },
        )
        return JsonResponse({"ok": True})

    return JsonResponse({"error": "Invalid action."}, status=400)


@login_required
def doctor_note_endpoint(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user.role != "doctor" or chat.doctor != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if not chat.child:
        return JsonResponse({"error": "This chat has no linked child record."}, status=400)

    note, _ = DoctorNote.objects.get_or_create(
        chat=chat,
        doctor=request.user,
        defaults={"child": chat.child},
    )

    if request.method == "GET":
        return JsonResponse(
            {
                "note": _serialize_doctor_note(note),
                "template_defaults": DOCTOR_NOTE_TEMPLATE_DEFAULTS,
            }
        )

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    template_type = (payload.get("template_type") or "").strip()
    if template_type in dict(DoctorNote.TEMPLATE_CHOICES):
        note.template_type = template_type

    note.chief_complaint = payload.get("chief_complaint", note.chief_complaint)
    note.clinical_observations = payload.get("clinical_observations", note.clinical_observations)
    note.assessment = payload.get("assessment", note.assessment)
    note.plan = payload.get("plan", note.plan)
    note.follow_up_instructions = payload.get("follow_up_instructions", note.follow_up_instructions)
    note.is_finalized = bool(payload.get("is_finalized", note.is_finalized))
    note.child = chat.child
    note.save()

    # Sync a live snapshot to the child profile record so notes stay attached to the patient record.
    chat.child.notes = _note_snapshot_for_child_record(note)
    chat.child.save(update_fields=["notes"])

    return JsonResponse({"ok": True, "note": _serialize_doctor_note(note)})
