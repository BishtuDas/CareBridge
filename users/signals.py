from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.dispatch import receiver


@receiver(user_logged_in)
def enforce_single_session(sender, request, user, **kwargs):
    if not request.session.session_key:
        request.session.save()

    new_session_key = request.session.session_key
    old_session_key = user.current_session_key

    if old_session_key and old_session_key != new_session_key:
        Session.objects.filter(session_key=old_session_key).delete()

    if user.current_session_key != new_session_key:
        user.current_session_key = new_session_key
        user.save(update_fields=["current_session_key"])


@receiver(user_logged_out)
def clear_session_key(sender, request, user, **kwargs):
    if not user:
        return

    if request.session.session_key and user.current_session_key == request.session.session_key:
        user.current_session_key = ""
        user.save(update_fields=["current_session_key"])
