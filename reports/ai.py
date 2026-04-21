import os

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from openai import OpenAI

from users.models import OpenAISettings


def _get_api_key():
    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if api_key:
        return api_key

    try:
        settings_row = OpenAISettings.objects.first()
        return (settings_row.api_key if settings_row else "") or ""
    except (OperationalError, ProgrammingError):
        return ""


def summarize_text(text):
    if not text:
        return ""

    api_key = _get_api_key()
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    prompt = (
        "Summarize the medical report in simple, non-medical language for a parent. "
        "Keep it short and clear."
    )
    truncated = text[:4000]

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": truncated},
            ],
        )
    except Exception:
        return ""

    try:
        return response.output[0].content[0].text.strip()
    except Exception:
        return ""


def summarize_for_doctor(text):
    if not text:
        return ""

    api_key = _get_api_key()
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    prompt = (
        "Summarize the medical report for a doctor. Include key findings, abnormalities, "
        "possible clinical concerns, and suggested next review steps. Keep concise and structured."
    )
    truncated = text[:5000]

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": truncated},
            ],
        )
    except Exception:
        return ""

    try:
        return response.output[0].content[0].text.strip()
    except Exception:
        return ""
