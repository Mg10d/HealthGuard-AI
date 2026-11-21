import json
from datetime import datetime
import streamlit as st

# Load GEMINI_API_KEY / GEMINI_MODEL from a local .env file if one exists.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; environment variables still work

from extractor import extract_symptoms
from safety_rules import assess_case, CARE_LEVELS

st.set_page_config(page_title="HealthGuard AI", page_icon="🛡️", layout="wide")

st.title("🛡️ HealthGuard AI")
st.subheader("AI-assisted early health risk screening")
st.info(
    "Prototype notice: This tool is for demonstration and early-awareness research only. "
    "It does not diagnose, rule out emergencies, or replace a qualified healthcare professional. "
    "If someone may be experiencing a medical emergency, contact local emergency services immediately."
)

with st.sidebar:
    st.header("About this prototype")
    st.write("Phase 1: text input, structured extraction, transparent red-flag rules, and care guidance.")
    st.write("No patient data is saved to a database in this phase.")
    st.write("LLM extraction is optional and requires a Gemini API key in your environment.")
    st.divider()
    st.caption("Do not enter real names, phone numbers, addresses, or other identifying information.")

st.markdown("### 1. Describe the symptoms")
description = st.text_area(
    "What is the person experiencing?",
    placeholder="Example: I have had a headache since yesterday. It is mild. I do not have chest pain or trouble breathing.",
    height=150,
    help="Describe symptoms, how long they have been present, their severity, and any relevant context. Avoid identifying information."
)

col1, col2 = st.columns(2)
with col1:
    age_group = st.selectbox(
        "Age group (optional)",
        ["Not provided", "Child (under 12)", "Teen (12–17)", "Adult (18–64)", "Older adult (65+)"]
    )
with col2:
    language = st.selectbox("Input language", ["English", "Other / mixed language"])

consent = st.checkbox(
    "I understand this is a non-diagnostic prototype and not a substitute for professional care."
)

if st.button("Assess symptoms", type="primary", use_container_width=True):
    if not description.strip():
        st.warning("Please describe the symptoms before continuing.")
    elif not consent:
        st.warning("Please confirm that you understand the prototype's limitations.")
    else:
        with st.spinner("Extracting information and checking safety rules..."):
            extracted, extraction_source, extraction_note = extract_symptoms(description)

            # Preserve the user's original description for conservative safety checks.
            assessment = assess_case(description, extracted, age_group)

        st.session_state["last_assessment"] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "extracted": extracted,
            "extraction_source": extraction_source,
            "extraction_note": extraction_note,
            "assessment": assessment,
            "age_group": age_group,
            "language": language,
        }

if "last_assessment" in st.session_state:
    record = st.session_state["last_assessment"]
    extracted = record["extracted"]
    assessment = record["assessment"]

    st.divider()
    st.markdown("### 2. Extracted information")
    st.caption(f"Extraction method: {record['extraction_source']}. {record['extraction_note']}")

    left, right = st.columns(2)
    with left:
        st.write("**Symptoms identified**")
        symptoms = extracted.get("symptoms", [])
        st.write(", ".join(symptoms) if symptoms else "No symptom was confidently extracted.")
        st.write("**Severity**")
        st.write(extracted.get("severity") or "Not provided")
        st.write("**Duration**")
        st.write(extracted.get("duration") or "Not provided")
    with right:
        st.write("**Relevant context**")
        context = extracted.get("context", [])
        st.write(", ".join(context) if context else "Not provided")
        st.write("**Negated symptoms**")
        negated = extracted.get("negated_symptoms", [])
        st.write(", ".join(negated) if negated else "None extracted")
        st.write("**Missing information**")
        missing = extracted.get("missing_information", [])
        st.write(", ".join(missing) if missing else "No required field flagged by the extractor")

    with st.expander("Review/edit extracted fields"):
        st.caption("Extraction can be wrong. Check these fields before relying on the summary.")
        corrected_symptoms = st.text_input(
            "Symptoms (comma-separated)",
            value=", ".join(extracted.get("symptoms", []))
        )
        corrected_severity = st.selectbox(
            "Severity",
            ["Not provided", "Mild", "Moderate", "Severe", "Unclear"],
            index=["Not provided", "Mild", "Moderate", "Severe", "Unclear"].index(
                extracted.get("severity") if extracted.get("severity") in
                ["Not provided", "Mild", "Moderate", "Severe", "Unclear"] else "Not provided"
            )
        )
        corrected_duration = st.text_input("Duration", value=extracted.get("duration") or "")
        if st.button("Reassess using corrected fields"):
            edited = dict(extracted)
            edited["symptoms"] = [x.strip() for x in corrected_symptoms.split(",") if x.strip()]
            edited["severity"] = None if corrected_severity == "Not provided" else corrected_severity
            edited["duration"] = corrected_duration.strip() or None
            record["extracted"] = edited
            record["assessment"] = assess_case(description, edited, age_group)
            st.session_state["last_assessment"] = record
            st.rerun()

    st.markdown("### 3. Preliminary screening result")
    level = assessment["risk_level"]
    if level == "High-risk":
        st.error(f"Risk category: {level}")
    elif level == "Uncertain":
        st.warning(f"Risk category: {level}")
    elif level == "Moderate-risk":
        st.warning(f"Risk category: {level}")
    else:
        st.info(f"Risk category: {level}")

    st.markdown("**Recommended next step**")
    st.write(assessment["recommendation"])

    if assessment["red_flags"]:
        st.markdown("**Safety rule(s) triggered**")
        for flag in assessment["red_flags"]:
            st.write(f"- {flag}")
    else:
        st.write("No configured red-flag phrase was detected. This does not prove that the situation is safe.")

    st.markdown("**Why this result was produced**")
    for reason in assessment["reasons"]:
        st.write(f"- {reason}")

    if assessment["risk_level"] in ("High-risk", "Uncertain"):
        st.warning(
            "Human review: this case should be reviewed by a qualified person where available. "
            "Do not delay emergency care while waiting for review."
        )

    st.markdown("### 4. Prototype audit summary")
    audit = {
        "timestamp": record["timestamp"],
        "extraction_method": record["extraction_source"],
        "risk_level": assessment["risk_level"],
        "red_flags": assessment["red_flags"],
        "reasons": assessment["reasons"],
        "human_review_recommended": assessment["human_review_recommended"],
        "prototype_note": "Not a diagnosis; no database persistence in Phase 1."
    }
    st.json(audit)
    st.download_button(
        "Download this screening summary (JSON)",
        data=json.dumps(audit, indent=2),
        file_name="healthguard_screening_summary.json",
        mime="application/json"
    )

st.divider()
st.caption(
    "HealthGuard AI Phase 1 prototype • Results depend on the accuracy of user input, extraction, "
    "and the limited demonstration rules. This has not been clinically validated."
)
