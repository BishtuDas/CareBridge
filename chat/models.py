from django.conf import settings
from django.db import models


class Chat(models.Model):
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_chats"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_chats"
    )
    child = models.ForeignKey(
        "children.Child",
        on_delete=models.CASCADE,
        related_name="chats",
        null=True,
        blank=True,
    )

    def __str__(self):
        child_name = self.child.name if self.child else "Unknown"
        return f"Chat: {self.parent} -> {self.doctor} ({child_name})"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    attachment = models.FileField(upload_to="chat_attachments/", blank=True, null=True)
    is_ai_generated = models.BooleanField(default=False)
    ai_generation_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.text[:30]}"


class DoctorAIResponse(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="ai_responses")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_ai_responses"
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_ai_responses"
    )
    child = models.ForeignKey("children.Child", on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI response for chat {self.chat_id}"


class AIDraftReply(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_EDITED_SENT = "edited_sent"
    STATUS_REMOVED = "removed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_EDITED_SENT, "Edited and sent"),
        (STATUS_REMOVED, "Removed"),
    )

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="ai_draft_replies")
    source_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="ai_draft_replies",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_ai_draft_replies",
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_ai_draft_replies",
    )
    child = models.ForeignKey("children.Child", on_delete=models.CASCADE, null=True, blank=True)

    patient_problem_json = models.JSONField(default=dict, blank=True)
    generated_reply = models.TextField(blank=True)
    edited_reply = models.TextField(blank=True)
    removal_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI draft {self.id} for chat {self.chat_id} ({self.status})"


class DoctorNote(models.Model):
    TEMPLATE_INITIAL_ASSESSMENT = "initial_assessment"
    TEMPLATE_FOLLOW_UP = "follow_up"
    TEMPLATE_DIAGNOSIS = "diagnosis"
    TEMPLATE_CHOICES = (
        (TEMPLATE_INITIAL_ASSESSMENT, "Initial Assessment"),
        (TEMPLATE_FOLLOW_UP, "Follow-up"),
        (TEMPLATE_DIAGNOSIS, "Diagnosis"),
    )

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="doctor_notes")
    child = models.ForeignKey("children.Child", on_delete=models.CASCADE, related_name="doctor_notes")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_notes",
    )
    template_type = models.CharField(max_length=40, choices=TEMPLATE_CHOICES, default=TEMPLATE_INITIAL_ASSESSMENT)
    chief_complaint = models.TextField(blank=True)
    clinical_observations = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=["chat", "doctor"], name="unique_doctor_note_per_chat_doctor"),
        ]

    def __str__(self):
        return f"Doctor note chat={self.chat_id} doctor={self.doctor_id}"
