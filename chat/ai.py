import os
import json

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


def _extract_response_text(response):
    try:
        if getattr(response, "output_text", None):
            return response.output_text.strip()
    except Exception:
        pass

    try:
        return response.output[0].content[0].text.strip()
    except Exception:
        return ""


def _looks_like_greeting(text):
    cleaned = (text or "").strip().lower()
    greeting_words = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
    return cleaned in greeting_words


def _looks_like_report_question(text):
    cleaned = (text or "").strip().lower()
    keywords = ("report", "reports", "summary", "lab", "test", "result", "results", "see my report")
    return any(keyword in cleaned for keyword in keywords)


def _clean_chat_reply(text):
    if not text:
        return ""

    lines = []
    blocked_prefixes = ("subject:", "dear ", "best regards", "regards", "sincerely", "best,", "thanks,")
    for raw_line in str(text).splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith(blocked_prefixes):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        lines.append(stripped)

    cleaned = " ".join(lines)
    cleaned = cleaned.replace("  ", " ").strip()
    return cleaned


def _default_reply_options(patient_name, patient_message=""):
    name_part = f" {patient_name}" if patient_name else ""
    if _looks_like_report_question(patient_message):
        return [
            f"Yes{name_part}, I can see your report. I’m reviewing it now.",
            f"Yes{name_part}, I have your report open. Tell me if you have any symptoms or concerns.",
            f"I can see your report{name_part}. I’ll review the findings and guide you on the next step.",
        ]
    return [
        f"Hello{name_part}, how can I help you today?",
        f"Hi{name_part}, thanks for reaching out. Please share the main symptoms and since when they started.",
        f"Hello{name_part}, I am here to help. Could you describe what concerns you most right now?",
    ]


def suggest_reply(report_summaries, last_message):
    if not report_summaries and not last_message:
        return ""

    api_key = _get_api_key()
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    prompt = (
        "You are a doctor replying in a live chat with a parent. Write natural chat messages, not email. "
        "Never use Subject, Dear Doctor, Best regards, signatures, or letter formatting. "
        "Use the patient name if available. Keep replies short, warm, and clinically safe."
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

    return _clean_chat_reply(_extract_response_text(response))


def answer_from_reports(report_summaries, report_texts, question):
    if not question:
        return ""

    api_key = _get_api_key()
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

    return _extract_response_text(response)


def build_patient_problem_and_reply(report_summaries, report_texts, patient_message, patient_name=""):
    if not patient_message:
        return {}

    api_key = _get_api_key()
    if not api_key:
        return {}

    client = OpenAI(api_key=api_key)
    prompt = (
        "You support pediatric tele-consult triage in a live chat. Read the patient/parent message and output "
        "strict JSON with keys: concern_summary (string), urgency (one of low, medium, high), "
        "symptoms (array of strings), recommended_next_step (string), auto_send_greeting (boolean), "
        "doctor_draft_reply (string), reply_options (array with 3 short reply options for doctor). "
        "Never use email formatting like Subject, Dear Doctor, or Best regards. "
        "If message is about a report/result/summary, make the reply options about seeing and reviewing the report. "
        "If message is a greeting like hello/hi and no symptoms are mentioned, include friendly doctor greeting options using patient name if available. Keep concise and chat-like."
    )
    context = (
        "Patient name:\n"
        f"{patient_name}\n\n"
        "Report summaries:\n"
        f"{report_summaries}\n\n"
        "Report text:\n"
        f"{report_texts}\n\n"
        "Patient message:\n"
        f"{patient_message}"
    )
    truncated = context[:7000]

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": truncated},
            ],
        )
    except Exception:
        return {}

    raw = _extract_response_text(response)
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except Exception:
        return {
            "concern_summary": patient_message[:200],
            "urgency": "low",
            "symptoms": [],
            "recommended_next_step": "Doctor review required.",
            "auto_send_greeting": _looks_like_greeting(patient_message),
            "doctor_draft_reply": suggest_reply(report_summaries, patient_message),
            "reply_options": _default_reply_options(patient_name, patient_message),
        }

    reply_options = parsed.get("reply_options") or []
    if not isinstance(reply_options, list):
        reply_options = []

    cleaned_options = []
    for option in reply_options:
        if isinstance(option, str) and option.strip():
            cleaned_options.append(option.strip())

    if len(cleaned_options) < 3:
        cleaned_options = _default_reply_options(patient_name, patient_message)

    if _looks_like_report_question(patient_message):
        report_options = _default_reply_options(patient_name, patient_message)
        cleaned_options = (cleaned_options + report_options)[:3]

    return {
        "concern_summary": (parsed.get("concern_summary") or "").strip(),
        "urgency": (parsed.get("urgency") or "low").strip().lower(),
        "symptoms": parsed.get("symptoms") or [],
        "recommended_next_step": (parsed.get("recommended_next_step") or "").strip(),
        "auto_send_greeting": bool(parsed.get("auto_send_greeting")),
        "doctor_draft_reply": _clean_chat_reply(parsed.get("doctor_draft_reply") or "") or cleaned_options[0],
        "reply_options": cleaned_options[:3] if cleaned_options else _default_reply_options(patient_name, patient_message),
    }
