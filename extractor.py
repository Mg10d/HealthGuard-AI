"""Structured symptom extraction with optional Gemini API and a safe local fallback."""
import json
import os
import re

SCHEMA_KEYS = [
    "symptoms", "severity", "duration", "context",
    "negated_symptoms", "missing_information"
]

SYSTEM_INSTRUCTIONS = """
You extract facts from a user's health description for a non-diagnostic screening prototype.
Return ONLY valid JSON with exactly these keys:
{
  "symptoms": ["symptom phrase"],
  "severity": "Mild" | "Moderate" | "Severe" | "Unclear" | null,
  "duration": "short text" | null,
  "context": ["relevant facts explicitly stated"],
  "negated_symptoms": ["symptoms the user explicitly denies"],
  "missing_information": ["important fields not stated"]
}
Rules:
- Extract only what the user explicitly says. Do not diagnose, infer a disease, recommend medication, or invent details.
- Distinguish negated symptoms (e.g. "no chest pain") from present symptoms.
- If severity or duration is not stated, use null.
- If a statement is ambiguous, preserve uncertainty in missing_information.
- Do not treat this task as a clinical decision.
"""

def _empty_result():
    return {
        "symptoms": [],
        "severity": None,
        "duration": None,
        "context": [],
        "negated_symptoms": [],
        "missing_information": ["severity", "duration", "relevant context"]
    }

def _normalize(data):
    """Validate model output and normalize fields before the app uses it."""
    if not isinstance(data, dict):
        return _empty_result()
    result = _empty_result()
    result["symptoms"] = _as_list(data.get("symptoms"))
    result["context"] = _as_list(data.get("context"))
    result["negated_symptoms"] = _as_list(data.get("negated_symptoms"))
    result["missing_information"] = _as_list(data.get("missing_information"))
    severity = data.get("severity")
    if isinstance(severity, str) and severity.strip().lower() in {
        "mild", "moderate", "severe", "unclear"
    }:
        result["severity"] = severity.strip().capitalize()
    duration = data.get("duration")
    if isinstance(duration, str) and duration.strip():
        result["duration"] = duration.strip()[:200]
    return result

def _as_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:160] for item in value if str(item).strip()][:30]

def _local_fallback(text):
    """Conservative fallback; it is not a substitute for an LLM or clinical NLP."""
    result = _empty_result()
    lower = text.lower()

    known = [
        "chest pain", "shortness of breath", "difficulty breathing",
        "trouble breathing", "headache", "fever", "cough", "vomiting",
        "diarrhea", "dizziness", "abdominal pain", "stomach pain",
        "sore throat", "rash", "weakness", "numbness", "bleeding",
        "confusion", "fainting", "vision changes"
    ]
    negated = []
    present = []
    for symptom in known:
        # Detect simple local negation patterns; complex language may be missed.
        patterns = [
            rf"\bno\s+(?:signs of\s+)?{re.escape(symptom)}\b",
            rf"\bnot\s+(?:having\s+)?{re.escape(symptom)}\b",
            rf"\bdenies\s+{re.escape(symptom)}\b",
            rf"\bwithout\s+{re.escape(symptom)}\b"
        ]
        if any(re.search(p, lower) for p in patterns):
            negated.append(symptom)
        elif symptom in lower:
            present.append(symptom)

    result["symptoms"] = present
    result["negated_symptoms"] = negated

    if re.search(r"\b(severe|very bad|extreme|unbearable)\b", lower):
        result["severity"] = "Severe"
    elif re.search(r"\b(moderate|quite bad)\b", lower):
        result["severity"] = "Moderate"
    elif re.search(r"\b(mild|slight|slightly)\b", lower):
        result["severity"] = "Mild"

    duration_match = re.search(
        r"\b(?:for|since)\s+((?:\d+\s*)?(?:minutes?|hours?|days?|weeks?|months?|years?|yesterday|today))\b",
        lower
    )
    if duration_match:
        result["duration"] = duration_match.group(1)

    result["missing_information"] = []
    if not result["symptoms"]:
        result["missing_information"].append("symptoms")
    if not result["severity"]:
        result["missing_information"].append("severity")
    if not result["duration"]:
        result["missing_information"].append("duration")
    if not result["context"]:
        result["missing_information"].append("relevant context")
    return result

def extract_symptoms(text):
    """
    Returns (validated_structured_data, method_label, note).
    Uses Gemini only when GEMINI_API_KEY is configured. Otherwise uses a basic fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            response = client.models.generate_content(
                model=model_name,
                contents=SYSTEM_INSTRUCTIONS + "\n\nUser description:\n" + text[:6000],
                config={"response_mime_type": "application/json", "temperature": 0}
            )
            data = json.loads(response.text)
            normalized = _normalize(data)
            return normalized, f"Gemini ({model_name})", (
                "Model output was schema-checked. Please review extracted fields; errors remain possible."
            )
        except Exception as exc:
            # Avoid exposing provider response or user input in logs/UI.
            fallback = _local_fallback(text)
            return fallback, "Local fallback (LLM unavailable)", (
                "The configured LLM request failed or returned invalid output. "
                "Fallback extraction is basic and may miss symptoms or negation."
            )

    return _local_fallback(text), "Local fallback (no API key)", (
        "Add GEMINI_API_KEY to enable LLM extraction. The current keyword-based fallback is limited."
    )
