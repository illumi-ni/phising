"""Rule-based tactic labeling for phishing email text.

Detects persuasion tactics by keyword matching. Confidence is the ratio of
matched keywords to the total keyword list size for that tactic, capped at 1.0.
"""

TACTIC_KEYWORDS: dict[str, list[str]] = {
    "urgency": [
        "act now",
        "immediately",
        "24 hours",
        "expire",
        "urgent",
        "as soon as possible",
        "right away",
        "today",
        "within",
        "deadline",
        "immediate action",
    ],
    "authority": [
        "it department",
        "your bank",
        "official notice",
        "security team",
        "administrator",
        "management",
        "finance department",
        "technical support",
        "help desk",
    ],
    "scarcity": [
        "limited",
        "last chance",
        "one time only",
        "only a few",
        "while supplies last",
        "exclusive offer",
        "only today",
    ],
    "fear": [
        "suspended",
        "unauthorized access",
        "security breach",
        "account locked",
        "compromised",
        "legal action",
        "penalty",
        "fraudulent activity",
        "terminated",
    ],
    "curiosity": [
        "you won't believe",
        "click to see",
        "find out what",
        "secret",
        "surprise",
        "shocking",
        "exclusive",
        "you have to see",
        "interesting",
    ],
}


def label_tactics(text: str) -> list[dict]:
    """Return a list of {tactic_type, confidence} detected in the text.

    Confidence = matched_keywords / total_keywords_for_tactic, capped at 1.0.
    Only tactics with at least one match are returned; if nothing matches,
    a single 'other' entry with confidence 0.0 is returned.
    """
    lowered = text.lower()
    results = []

    for tactic, keywords in TACTIC_KEYWORDS.items():
        matched = sum(1 for kw in keywords if kw in lowered)
        if matched > 0:
            confidence = min(matched / len(keywords), 1.0)
            results.append(
                {
                    "tactic_type": tactic,
                    "confidence": round(confidence, 3),
                }
            )

    if not results:
        results.append({"tactic_type": "other", "confidence": 0.0})

    return results


if __name__ == "__main__":
    sample = (
        "URGENT: Act now! Your account will be suspended within 24 hours "
        "if you do not verify immediately. This is an official notice from "
        "the IT department. Last chance to avoid a security breach."
    )
    print(label_tactics(sample))
