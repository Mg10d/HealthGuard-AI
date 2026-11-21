# HealthGuard AI — Phase 1 Prototype

A Streamlit prototype for **AI-assisted early health risk screening**. It accepts text input, extracts symptom details, applies transparent demonstration red-flag rules, provides a preliminary routing recommendation, explains the result, and suggests human review for high-risk or uncertain cases.

## Scope

This implements Phase 1 of the HealthGuard AI synopsis:
- Text-based symptom entry
- Structured symptom extraction through Gemini when configured
- A limited keyword-based fallback when no API key is available
- Transparent Python red-flag rules
- Preliminary risk labels and care guidance
- Explanations and a downloadable JSON audit summary
- No persistent patient database in Phase 1

## Important safety limitations

- This is an educational prototype, not a medical device or clinically validated triage system.
- It does not diagnose, rule out illness, or replace professional medical judgment.
- The included red-flag rules are intentionally limited examples, not a complete clinical protocol.
- Phrase matching and basic negation detection can miss emergencies or trigger incorrectly.
- A “Low-risk” result does **not** mean that a person is safe.
- Emergency concerns should be directed to local emergency services; do not wait for AI or a reviewer.
- Do not enter identifying or real patient data in this prototype.
- Before real-world testing, obtain appropriate institutional approval and qualified clinical review.

## Requirements

- Python 3.10 or newer recommended
- Internet access and a Gemini API key only if you want LLM extraction
- Without an API key, the app uses a limited local keyword fallback

## Windows setup (PowerShell)

Open PowerShell in this folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

## Configure Gemini (optional)

1. Copy `.env.example` to `.env`.
2. Put your key in `.env` as `GEMINI_API_KEY=your_key_here`.
3. Run the app. `app.py` loads `.env` automatically (via `python-dotenv`, included in `requirements.txt`).

For the simplest environment-only setup in PowerShell:

```powershell
$env:GEMINI_API_KEY="your_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash"
streamlit run app.py
```

Do not commit `.env` or share your API key. Environment variables set in the terminal also work.

## Run

```powershell
streamlit run app.py
```

Streamlit opens the app in your browser, usually at `http://localhost:8501`.

## Project structure

```text
healthguard_ai_phase1/
├── app.py
├── extractor.py
├── safety_rules.py
├── negation.py          # shared clause-aware negation helper
├── tests/
│   ├── conftest.py
│   └── test_cases.py    # 32 fictional regression tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Automated tests

```powershell
pytest -v
```

The suite runs 32 fictional cases through the local fallback (no API key needed) and checks the risk level, red flags, and present/denied symptoms. Run it after every change. Passing tests show the prototype behaves as designed; they do not show clinical safety.

## Suggested manual test cases

Use fictional examples only.

1. Mild headache for one day, explicitly described as mild.
2. Moderate cough for three days.
3. Severe symptom description.
4. Chest pain with difficulty breathing.
5. Explicit denial such as “I do not have chest pain.”
6. Very vague description with no duration or severity.
7. An ambiguous description containing multiple symptoms and negation.

For each test, verify the extracted fields, rule triggers, risk label, explanation, and recommendation. The rules are not comprehensive, so do not treat a missed trigger as proof of safety.

## Next phases

- Phase 2: curate a suitable labelled dataset, establish a split that avoids leakage, compare Logistic Regression, Random Forest, and XGBoost, and evaluate per-class precision/recall/F1 plus a confusion matrix.
- Phase 3: add voice transcription, PostgreSQL persistence, PDF reports, reviewer workflow, and an audit trail.
- Phase 4: add SHAP, symptom progression, probability calibration, and uncertainty methods only when supported by data and evaluation.
