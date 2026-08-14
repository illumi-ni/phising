"""LLM email generation for phishing scenarios.

Uses an OpenAI-compatible chat completions API (default: Groq free tier).
When no API key is configured, falls back to a deterministic template-based
generator so the pipeline remains testable end-to-end.
"""
import json
import logging
import os
from datetime import datetime, timezone

from ..models import Scenario

logger = logging.getLogger("llm_generator")
# Must be INFO or the audit log below would be dropped (default is WARNING)
logger.setLevel(logging.INFO)

# Log to a file inside the container so prompts/responses are auditable
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_file_handler = logging.FileHandler(os.path.join(_LOG_DIR, "llm_generator.log"))
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
)
logger.addHandler(_file_handler)

SYSTEM_PROMPT = (
    "You are generating SYNTHETIC email content for a controlled lab research "
    "environment. This is a phishing-detection research benchmark. All emails "
    "you produce are fictional, synthetic, and clearly intended for research "
    "and defensive model training only — they must never be sent to real "
    "people. Produce a realistic example of a phishing-style email following "
    "the scenario instructions below."
)

PROMPT_TEMPLATES = {
    "password_reset": (
        "Scenario: A fraudulent password reset notification.\n"
        "Tone: {tone}. Urgency level (1-5): {urgency}.\n"
        "Write a convincing password-reset email body that a phishing "
        "attacker might use, including a fake reset link placeholder. "
        "Return a JSON object with keys \"subject\" and \"body\"."
    ),
    "invoice": (
        "Scenario: A fake invoice / payment reminder.\n"
        "Tone: {tone}. Urgency level (1-5): {urgency}.\n"
        "Write a convincing fake-invoice email body referencing an unpaid "
        "invoice, with a payment link placeholder. "
        "Return a JSON object with keys \"subject\" and \"body\"."
    ),
    "it_alert": (
        "Scenario: A fraudulent IT security alert.\n"
        "Tone: {tone}. Urgency level (1-5): {urgency}.\n"
        "Write a convincing IT security alert email body claiming suspicious "
        "activity on the account, with a verification link placeholder. "
        "Return a JSON object with keys \"subject\" and \"body\"."
    ),
}

# Defaults: Groq free tier (OpenAI-compatible)
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


def _build_messages(scenario: Scenario) -> dict:
    template = PROMPT_TEMPLATES.get(
        scenario.type.value, PROMPT_TEMPLATES["password_reset"]
    )
    user_prompt = template.format(
        tone=scenario.tone, urgency=scenario.urgency_level
    )
    return {
        "system": SYSTEM_PROMPT,
        "user": user_prompt,
    }


def _parse_output(raw: str) -> tuple[str, str]:
    """Parse the model's JSON response into (subject, body)."""
    try:
        # Model sometimes wraps JSON in code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)
        return data["subject"], data["body"]
    except Exception:
        # Fallback: first non-empty line = subject, rest = body
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
        subject = lines[0] if lines else "Synthetic phishing email"
        body = "\n".join(lines[1:]) if len(lines) > 1 else raw.strip()
        return subject, body


def _template_email(scenario: Scenario) -> tuple[str, str]:
    """Deterministic fallback generator (no API key required)."""
    urgency_map = {
        5: "URGENT: Your account requires immediate action",
        4: "IMPORTANT: Action required within 24 hours",
        3: "Notice: Please review and respond",
        2: "Reminder: Update needed",
        1: "Friendly reminder",
    }
    subject = urgency_map.get(
        scenario.urgency_level, "Action required"
    )
    bodies = {
        "password_reset": (
            f"Dear user,\n\nYour password reset request has been processed. "
            f"If you did not request this change, please verify your account "
            f"immediately at https://secure-portal.example.com/reset "
            f"(tone: {scenario.tone}).\n\nAccount Security Team"
        ),
        "invoice": (
            f"Dear customer,\n\nOur records show invoice #4821 is past due. "
            f"Please settle the outstanding balance promptly to avoid service "
            f"interruption: https://billing.example.com/pay (tone: {scenario.tone}).\n\n"
            f"Billing Department"
        ),
        "it_alert": (
            f"Dear employee,\n\nWe detected unusual sign-in activity on your "
            f"account. Verify your credentials now to prevent suspension: "
            f"https://sso-portal.example.com/verify (tone: {scenario.tone}).\n\n"
            f"IT Security Operations"
        ),
    }
    body = bodies.get(scenario.type.value, bodies["password_reset"])
    return subject, body


def generate_email(scenario: Scenario) -> dict:
    """Generate a phishing-style email for the scenario.

    Returns dict with keys: subject, body, model_used, prompt_used.
    """
    messages = _build_messages(scenario)
    prompt_used = json.dumps(messages, indent=2)

    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.getenv("LLM_API_KEY", "").strip()

    raw_response = None
    model_used = model

    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": messages["system"]},
                    {"role": "user", "content": messages["user"]},
                ],
                temperature=0.8,
                max_tokens=800,
            )
            raw_response = resp.choices[0].message.content
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("LLM call failed (%s); using template fallback", exc)
            raw_response = None
            model_used = "template-fallback"
    else:
        logger.info("No LLM_API_KEY set; using template fallback generator")
        model_used = "template-fallback"

    if raw_response is None:
        subject, body = _template_email(scenario)
    else:
        subject, body = _parse_output(raw_response)

    # Audit log: full prompt, raw response, scenario_id, timestamp, model name
    logger.info(
        "scenario_id=%s model=%s\nPROMPT:\n%s\nRAW_RESPONSE:\n%s\nSUBJECT=%s\nBODY=%s",
        scenario.id,
        model_used,
        prompt_used,
        raw_response if raw_response is not None else "(template fallback)",
        subject,
        body,
    )

    return {
        "subject": subject,
        "body": body,
        "model_used": model_used,
        "prompt_used": prompt_used,
    }
