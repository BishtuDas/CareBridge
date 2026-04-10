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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.text[:30]}"
