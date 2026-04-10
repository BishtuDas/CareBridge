from django.urls import path

from .views import chat_detail, chat_list, fetch_messages, start_chat

urlpatterns = [
    path("chats/", chat_list, name="chat_list"),
    path("chat/start/", start_chat, name="chat_start"),
    path("chat/<int:chat_id>/", chat_detail, name="chat_detail"),
    path("chat/<int:chat_id>/messages/", fetch_messages, name="fetch_messages"),
]
