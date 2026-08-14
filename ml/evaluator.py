"""Evaluation engine for phishing emails.

Scores:
- readability_score: Flesch Reading Ease (textstat)
- sentiment_score: VADER sentiment + urgency keyword density, 0-1
- persuasion_score: weighted persuasion trigger word count normalized by length
- similarity_score: max cosine similarity vs reference phishing embeddings
  (sentence-transformers all-MiniLM-L6-v2)
"""
import os
import re

import textstat

try:
    import nltk

    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)
except Exception:
    pass

from nltk.sentiment.vader import SentimentIntensityAnalyzer  # noqa: E402

from tactic_labeler import TACTIC_KEYWORDS  # noqa: E402

# ──────────────────────────────────────────────
# Lazy-loaded heavy resources
# ──────────────────────────────────────────────

_sia = None
_encoder = None
_reference_embeddings = None
_reference_texts = None


def _get_sia() -> SentimentIntensityAnalyzer:
    global _sia
    if _sia is None:
        _sia = SentimentIntensityAnalyzer()
    return _sia


def _get_encoder():
    """Lazily load the sentence-transformers model (downloads on first use)."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def _get_reference_embeddings(reference_texts: list[str]):
    """Cache embeddings for the reference phishing corpus."""
    global _reference_embeddings, _reference_texts
    if reference_texts is None or len(reference_texts) == 0:
        return []
    if _reference_embeddings is None or _reference_texts != reference_texts:
        encoder = _get_encoder()
        _reference_embeddings = encoder.encode(
            reference_texts, convert_to_tensor=True
        )
        _reference_texts = list(reference_texts)
    return _reference_embeddings


# ──────────────────────────────────────────────
# Individual scores
# ──────────────────────────────────────────────

def readability_score(text: str) -> float:
    """Flesch Reading Ease (0-100, higher = easier to read)."""
    if not text.strip():
        return 0.0
    return float(textstat.flesch_reading_ease(text))


def _urgency_density(text: str) -> float:
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0.0
    urgency_hits = sum(1 for kw in TACTIC_KEYWORDS["urgency"] if kw in text.lower())
    return min(urgency_hits / len(words) * 100, 1.0)


def sentiment_urgency_score(text: str) -> float:
    """Combine VADER compound (-1..1) with urgency density into a 0-1 score."""
    vader = _get_sia().polarity_scores(text)
    compound = (vader["compound"] + 1.0) / 2.0  # map -1..1 -> 0..1
    urgency = _urgency_density(text)
    return round(min(0.5 * compound + 0.5 * urgency, 1.0), 3)


def persuasion_score(text: str) -> float:
    """Weighted count of persuasion trigger words normalized by text length."""
    lowered = text.lower()
    words = re.findall(r"\w+", lowered)
    if not words:
        return 0.0
    triggers = 0
    for tactic in TACTIC_KEYWORDS.values():
        triggers += sum(1 for kw in tactic if kw in lowered)
    # Normalize: triggers per word, scaled by 10 for a readable 0-1 range
    return round(min(triggers / len(words) * 10, 1.0), 3)


def similarity_score(text: str, reference_texts: list[str]) -> float:
    """Max cosine similarity against reference phishing email embeddings."""
    if not reference_texts:
        return 0.0
    try:
        from sentence_transformers import util

        embeddings = _get_reference_embeddings(reference_texts)
        encoder = _get_encoder()
        query_emb = encoder.encode(text, convert_to_tensor=True)
        sims = util.cos_sim(query_emb, embeddings)
        return round(float(sims.max()), 3)
    except Exception:
        # Model unavailable (no network / too heavy): keyword-overlap fallback
        lowered = text.lower()
        all_kws = [kw for tactic in TACTIC_KEYWORDS.values() for kw in tactic]
        text_kws = {kw for kw in all_kws if kw in lowered}
        if not text_kws:
            return 0.0
        best = 0.0
        for ref in reference_texts:
            ref_kws = {kw for kw in all_kws if kw in ref.lower()}
            if ref_kws:
                best = max(best, len(ref_kws & text_kws) / len(text_kws))
        return round(min(best, 1.0), 3)


# ──────────────────────────────────────────────
# Combined entry point
# ──────────────────────────────────────────────

def evaluate_email(text: str, reference_texts: list[str] | None = None) -> dict:
    """Compute all four scores for an email body.

    Returns dict with keys readability_score, sentiment_score,
    persuasion_score, similarity_score.
    """
    refs = reference_texts or []
    return {
        "readability_score": readability_score(text),
        "sentiment_score": sentiment_urgency_score(text),
        "persuasion_score": persuasion_score(text),
        "similarity_score": similarity_score(text, refs),
    }


if __name__ == "__main__":
    sample = (
        "URGENT: Your account will be suspended within 24 hours. "
        "Verify immediately or you will lose access forever. "
        "This is your last chance to avoid a security breach."
    )
    print(evaluate_email(sample, ["URGENT: your account is compromised, act now"]))
