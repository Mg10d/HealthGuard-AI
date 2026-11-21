"""Shared, clause-aware negation helper for HealthGuard AI.

A negation word ("no", "not", "denies", ...) only applies to words that come
after it in the SAME clause. Clauses are split at punctuation and at contrast
words such as "but" / "however", so that:

    "no fever or cough"                    -> fever AND cough are negated
    "no fever but I have a cough"          -> only fever is negated
    "I'm not sure, but I have chest pain"  -> chest pain is NOT negated

This is still a simple heuristic, not clinical NLP. When in doubt it prefers
NOT to negate, because a missed symptom is more dangerous than an extra one.
"""
import re

# Split points between clauses.
CLAUSE_BREAK = re.compile(
    r"[.!?;,\n]|\b(?:but|however|although|though|except|yet|and now|then)\b"
)

# Words that negate what follows them in the same clause.
NEGATION_CUE = re.compile(
    r"\b(?:no|not|never|without|denies|denied|nor|none|free of|negative for|"
    r"don't|dont|doesn't|doesnt|didn't|didnt|haven't|havent|hasn't|hasnt|"
    r"isn't|isnt|aren't|arent|wasn't|wasnt)\b"
)

# Phrases that contain "not"/"no" but express uncertainty, not denial.
HEDGES = re.compile(r"\b(?:not sure|not certain|no idea|not know|don't know|dont know)\b")


def clause_before(text, pos):
    """Return the part of the clause that comes before position `pos`."""
    start = 0
    for m in CLAUSE_BREAK.finditer(text, 0, pos):
        start = m.end()
    return text[start:pos]


def is_negated(text, pos):
    """True if the word starting at `pos` is negated within its own clause.

    `text` should already be lower-case.
    """
    prefix = clause_before(text, pos)
    prefix = HEDGES.sub(" ", prefix)
    return bool(NEGATION_CUE.search(prefix))
