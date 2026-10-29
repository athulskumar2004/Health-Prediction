"""External AI integration (Google Gemini REST API).

Takes validated blood test values and returns a short, plain-language
risk assessment that is stored in the patient's Remarks field.
"""
import os
from datetime import date

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 30


class AIServiceError(Exception):
    """Raised when the AI API cannot produce a usable prediction."""


def _age(dob_iso):
    born = date.fromisoformat(dob_iso)
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def build_prompt(p):
    return (
        "You are a clinical decision-support assistant. Based ONLY on the blood test "
        "values below, name the most likely health condition(s) or risk(s), such as "
        "diabetes or pre-diabetes, anaemia or polycythaemia, or high cholesterol / "
        "cardiovascular risk. If all values are normal, say so.\n\n"
        f"Age: {_age(p['dob'])} years\n"
        f"Fasting glucose: {p['glucose']} mg/dL (normal 70-99)\n"
        f"Haemoglobin: {p['haemoglobin']} g/dL (normal about 12-17.5)\n"
        f"Total cholesterol: {p['cholesterol']} mg/dL (desirable below 200)\n\n"
        "Reply in plain text, maximum 40 words, no markdown. Start with the risk level "
        "(Low / Moderate / High), then the possible conditions, then advise consulting "
        "a doctor. This is a screening aid, not a diagnosis."
    )


def get_remarks(patient):
    """Call the AI API and return the remarks text. Raises AIServiceError on failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    payload = {
        "contents": [{"parts": [{"text": build_prompt(patient)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
    }
    try:
        resp = requests.post(
            API_URL.format(model=model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise AIServiceError(f"Could not reach the AI service: {exc.__class__.__name__}") from exc

    if resp.status_code != 200:
        raise AIServiceError(f"AI service returned HTTP {resp.status_code}")

    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise AIServiceError("AI service returned an unexpected response") from exc

    if not text:
        raise AIServiceError("AI service returned an empty response")
    return text
