import os

from dotenv import load_dotenv
from openai import OpenAI

from users.models import OpenAISettings


load_dotenv()


def summarize_text(text):
    if not text:
        return ""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        settings_row = OpenAISettings.objects.first()
        api_key = settings_row.api_key if settings_row else ""
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
