"""Transparent, conservative demonstration rules for HealthGuard AI.

These phrases are not a complete clinical triage protocol. Rules must be reviewed by
qualified clinicians before any real-world deployment.
"""
import re

from negation import is_negated

CARE_LEVELS = ("Low-risk", "Moderate-risk", "High-risk", "Uncertain")

# Conservative example triggers only. This list is intentionally incomplete.
RED_FLAG_RULES = [
    ("possible cardiac/respiratory emergency", [
        r"\bchest pain\b.*\b(shortness of breath|difficulty breathing|trouble breathing)\b",
        r"\b(shortness of breath|difficulty breathing|trouble breathing)\b.*\bchest pain\b",
        r"\bsevere (shortness of breath|difficulty breathing|breathing difficulty)\b",
        r"\bcan't breathe\b|\bcannot breathe\b|\bunable to breathe\b"
    ]),
    ("possible stroke warning signs", [
        r"\b(face droop|facial droop|one[- ]sided weakness|sudden weakness on one side)\b",
        r"\b(sudden difficulty speaking|slurred speech|sudden trouble speaking)\b"
    ]),
    ("loss of consciousness or severe confusion", [
        r"\b(unconscious|not waking up|unresponsive)\b",
        r"\bnew severe confusion\b"
    ]),
    ("severe bleeding", [
        r"\b(severe bleeding|bleeding heavily|bleeding that will not stop|bleeding that won't stop)\b"
    ]),
    ("possible severe allergic reaction", [
        r"\b(swelling of (the )?(tongue|throat))\b",
        r"\b(anaphylaxis|severe allergic reaction)\b"
    ]),
]

def _is_negated_near(text, match_start):
    """Clause-aware negation check (see negation.py); not clinical NLP.

    The old version looked 45 characters back across clause boundaries, so
    "I'm not sure, but I have chest pain and shortness of breath" suppressed the
    red flag. Negation now only applies inside the same clause.
    """
    suffix = text[match_start:match_start + 40].lower()
    return is_negated(text, match_start) or \
           bool(re.match(r"[^.!?,;]*\b(is absent|not present)\b", suffix))

def find_red_flags(text):
    found = []
    lower = text.lower()
    for label, patterns in RED_FLAG_RULES:
        triggered = False
        for pattern in patterns:
            for match in re.finditer(pattern, lower):
                if not _is_negated_near(lower, match.start()):
                    triggered = True
                    break
            if triggered:
                break
        if triggered:
            found.append(label)
    return found

def assess_case(original_text, extracted, age_group="Not provided"):
    """
    A transparent prototype policy, not a clinically validated triage algorithm.
    High-risk rule matches always override a model/extractor's low-risk impression.
    """
    flags = find_red_flags(original_text)
    symptoms = extracted.get("symptoms") or []
    severity = (extracted.get("severity") or "").lower()
    duration = (extracted.get("duration") or "").strip()
    missing = extracted.get("missing_information") or []

    reasons = []
    if flags:
        risk = "High-risk"
        reasons.extend([f"Configured safety rule matched: {flag}." for flag in flags])
        recommendation = (
            "Seek emergency medical help now or contact local emergency services. "
            "Do not wait for this prototype or a human reviewer before seeking help."
        )
        reasons.append("A matching red-flag rule takes priority over any model score.")
        human_review = True
    else:
        # "Unclear" severity is treated the same as missing. Previously it fell
        # through to the final branch and was labelled Low-risk.
        if severity == "unclear":
            severity = ""
        # Conservative uncertainty: limited extraction or missing core information.
        if not symptoms or not severity or not duration:
            risk = "Uncertain"
            reasons.append("One or more core assessment fields are missing or could not be extracted reliably.")
            if not symptoms:
                reasons.append("No symptom was confidently identified by the current extractor.")
            if not severity:
                reasons.append("Severity was not confidently provided.")
            if not duration:
                reasons.append("Duration was not confidently provided.")
            recommendation = (
                "Provide the missing details if safe to do so, and contact a qualified healthcare professional "
                "for advice if you are concerned or symptoms persist or worsen. This prototype cannot confirm safety."
            )
            human_review = True
        elif severity == "severe":
            risk = "High-risk"
            reasons.append("The input describes symptoms as severe; the prototype errs on the side of caution.")
            recommendation = (
                "Seek urgent medical assessment now. If symptoms are sudden, rapidly worsening, or feel life-threatening, "
                "contact local emergency services."
            )
            human_review = True
        elif severity == "moderate":
            risk = "Moderate-risk"
            reasons.append("The extracted severity is moderate; the system cannot determine the cause.")
            recommendation = (
                "Consider contacting a qualified healthcare professional for assessment, especially if symptoms persist, "
                "worsen, or new warning signs appear."
            )
            human_review = False
        else:
            risk = "Low-risk"
            reasons.append("No configured red-flag rule matched and the extracted severity was mild.")
            reasons.append("This category is a prototype routing label, not proof that the condition is safe.")
            recommendation = (
                "Monitor how you feel and consider routine professional advice if symptoms persist or concern you. "
                "Seek urgent help if warning signs develop or symptoms worsen."
            )
            human_review = False

    if age_group in ("Child (under 12)", "Older adult (65+)") and risk == "Low-risk":
        risk = "Uncertain"
        reasons.append("The prototype uses a conservative uncertainty flag for this age group.")
        recommendation = (
            "Seek advice from a qualified healthcare professional, particularly if symptoms persist or worsen. "
            "This prototype is not validated for age-specific triage."
        )
        human_review = True

    return {
        "risk_level": risk,
        "recommendation": recommendation,
        "red_flags": flags,
        "reasons": reasons,
        "human_review_recommended": human_review
    }
