from django.contrib import admin
from .models import Chat, DoctorAIResponse, DoctorNote, Message


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "parent", "doctor")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "text", "created_at")


@admin.register(DoctorAIResponse)
class DoctorAIResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "doctor", "parent", "child", "created_at")


@admin.register(DoctorNote)
class DoctorNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "child", "doctor", "template_type", "is_finalized", "updated_at")
    list_filter = ("template_type", "is_finalized")