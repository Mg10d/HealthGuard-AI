"""Regression tests for HealthGuard AI Phase 1 (fictional cases only).

Run from the project folder:   pytest -v

These tests use the local keyword fallback (no Gemini key) so results are
repeatable. Passing tests do NOT mean the system is clinically safe; they only
show that the prototype behaves the way we designed it.
"""
import pytest

from extractor import extract_symptoms
from safety_rules import assess_case


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Force the deterministic local fallback for every test."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def run(text, age="Not provided"):
    extracted, _, _ = extract_symptoms(text)
    return extracted, assess_case(text, extracted, age)


# (id, description, age group, expected risk, expected red-flag label or None)
RISK_CASES = [
    ("mild_headache", "I have had a mild headache since yesterday.", "Not provided", "Low-risk", None),
    ("moderate_cough", "Moderate cough for 3 days.", "Not provided", "Moderate-risk", None),
    ("severe_stomach", "Severe stomach pain for 2 hours.", "Not provided", "High-risk", None),
    ("chest_pain_breathing", "Chest pain and difficulty breathing since this morning.",
     "Not provided", "High-risk", "possible cardiac/respiratory emergency"),
    ("denied_chest_pain", "I do not have chest pain. Mild headache for 2 days.",
     "Not provided", "Low-risk", None),
    ("vague", "I feel unwell.", "Not provided", "Uncertain", None),
    ("no_fever_or_cough", "No fever or cough, mild sore throat for 2 days.",
     "Not provided", "Low-risk", None),
    ("not_severe", "Headache for 2 days, not severe.", "Not provided", "Uncertain", None),
    ("hedge_then_red_flag", "I'm not sure what's happening, but I have chest pain and shortness of breath.",
     "Not provided", "High-risk", "possible cardiac/respiratory emergency"),
    ("negation_then_but", "No fever but I have a cough, mild, for 3 days.", "Not provided", "Low-risk", None),
    ("child_mild", "Mild headache for one day.", "Child (under 12)", "Uncertain", None),
    ("older_adult_mild", "Mild headache for one day.", "Older adult (65+)", "Uncertain", None),
    ("cant_breathe", "I can't breathe.", "Not provided", "High-risk", "possible cardiac/respiratory emergency"),
    ("stroke_signs", "My father has face droop and slurred speech.", "Not provided", "High-risk",
     "possible stroke warning signs"),
    ("unresponsive", "He is unresponsive.", "Not provided", "High-risk",
     "loss of consciousness or severe confusion"),
    ("bleeding", "Bleeding heavily from a cut for 10 minutes.", "Not provided", "High-risk", "severe bleeding"),
    ("allergy", "Swelling of the tongue after eating peanuts.", "Not provided", "High-risk",
     "possible severe allergic reaction"),
    ("all_denied_then_mild", "No chest pain, no difficulty breathing. Mild cough for two days.",
     "Not provided", "Low-risk", None),
    ("isnt_very_bad", "Dizziness for a few hours, it isn't very bad.", "Not provided", "Uncertain", None),
    ("quite_bad_fever", "Fever for 2 days. It is quite bad.", "Not provided", "Moderate-risk", None),
    ("rash_a_week", "Mild rash for a week.", "Not provided", "Low-risk", None),
    ("cant_sleep", "I can't sleep and have a mild headache for 2 days.", "Not provided", "Low-risk", None),
    ("extremely_weak", "Vomiting since last night, extremely weak.", "Not provided", "High-risk", None),
    ("absent_suffix", "Chest pain is absent, mild cough for 2 days.", "Not provided", "Low-risk", None),
]


@pytest.mark.parametrize("case_id,text,age,expected_risk,expected_flag",
                         RISK_CASES, ids=[c[0] for c in RISK_CASES])
def test_risk_level(case_id, text, age, expected_risk, expected_flag):
    _, result = run(text, age)
    assert result["risk_level"] == expected_risk, result["reasons"]
    if expected_flag:
        assert expected_flag in result["red_flags"]
    else:
        assert result["red_flags"] == []


# Extraction details: which symptoms are present vs. denied.
EXTRACTION_CASES = [
    ("No fever or cough, mild sore throat for 2 days.", ["sore throat"], ["fever", "cough"]),
    ("No fever but I have a cough, mild, for 3 days.", ["cough"], ["fever"]),
    ("I do not have chest pain or trouble breathing.", [], ["chest pain", "trouble breathing"]),
    ("I can't sleep and have a mild headache for 2 days.", ["headache"], []),
    ("No fever earlier, but now I have a fever.", ["fever"], []),
]


@pytest.mark.parametrize("text,present,denied", EXTRACTION_CASES)
def test_extraction(text, present, denied):
    extracted, _ = run(text)
    assert sorted(extracted["symptoms"]) == sorted(present)
    assert sorted(extracted["negated_symptoms"]) == sorted(denied)


def test_not_severe_is_not_severe():
    extracted, _ = run("Headache for 2 days, not severe.")
    assert extracted["severity"] is None


def test_duration_words():
    extracted, _ = run("Mild cough for two days.")
    assert extracted["duration"] == "two days"


def test_unclear_severity_is_uncertain():
    """An 'Unclear' severity (e.g. from Gemini) must never become Low-risk."""
    extracted = {"symptoms": ["headache"], "severity": "Unclear", "duration": "2 days",
                 "context": [], "negated_symptoms": [], "missing_information": []}
    result = assess_case("headache for 2 days", extracted)
    assert result["risk_level"] == "Uncertain"
