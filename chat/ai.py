import os

from dotenv import load_dotenv
from openai import OpenAI

from users.models import OpenAISettings


load_dotenv()


def suggest_reply(report_summaries, last_message):
    if not report_summaries and not last_message:
        return ""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        settings_row = OpenAISettings.objects.first()
        api_key = settings_row.api_key if settings_row else ""
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    prompt = (
        "You are a medical assistant. Draft a short, professional reply for a doctor. "
        "Use the report summaries and the latest message. Keep it concise and safe."
    )
    context = f"Reports:\n{report_summaries}\n\nLatest message:\n{last_message}"
    truncated = context[:4000]

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


def answer_from_reports(report_summaries, report_texts, question):
    if not question:
        return ""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        settings_row = OpenAISettings.objects.first()
        api_key = settings_row.api_key if settings_row else ""
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    prompt = (
        "You are a clinical helper for doctors. Answer ONLY using the provided report "
        "summaries and report text. If the answer is not in the reports, say you do not "
        "have that information from the uploaded reports. Keep it concise."
    )
    context = (
        "Report summaries:\n"
        f"{report_summaries}\n\n"
        "Report text:\n"
        f"{report_texts}\n\n"
        "Question:\n"
        f"{question}"
    )
    truncated = context[:6000]

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
