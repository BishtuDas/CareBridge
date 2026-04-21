from django.urls import path

from .views import (
    chat_detail,
    chat_list,
    doctor_ai_draft_action,
    doctor_ai_help,
    doctor_note_endpoint,
    fetch_messages,
    start_chat,
)

urlpatterns = [
    path("chats/", chat_list, name="chat_list"),
    path("chat/start/", start_chat, name="chat_start"),
    path("chat/<int:chat_id>/", chat_detail, name="chat_detail"),
    path("chat/<int:chat_id>/messages/", fetch_messages, name="fetch_messages"),
    path("chat/<int:chat_id>/ai-help/", doctor_ai_help, name="doctor_ai_help"),
    path("chat/<int:chat_id>/doctor-notes/", doctor_note_endpoint, name="doctor_note_endpoint"),
    path(
        "chat/<int:chat_id>/ai-draft/<int:draft_id>/action/",
        doctor_ai_draft_action,
        name="doctor_ai_draft_action",
    ),
]
