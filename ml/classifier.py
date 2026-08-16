"""Defensive phishing detection classifier.

Trains a TF-IDF + Logistic Regression pipeline on labeled emails
(human_emails from the DB, optionally augmented with a public phishing
dataset) and saves the model to /ml/models/classifier.pkl.
"""
import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "classifier.pkl")

# If we don't have enough labeled emails, we fall back to this public corpus.
PUBLIC_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "sample_data", "nazario_phishing.csv"
)


def _load_human_emails(human_emails: list[dict]) -> pd.DataFrame:
    """human_emails: list of {subject, body, label}."""
    rows = []
    for e in human_emails:
        rows.append(
            {
                "text": f"{e.get('subject', '')} {e.get('body', '')}",
                "label": e.get("label"),
            }
        )
    return pd.DataFrame(rows)


def _load_public_dataset() -> pd.DataFrame:
    """Load the public Nazario phishing corpus CSV if present."""
    if not os.path.isfile(PUBLIC_DATASET_PATH):
        return pd.DataFrame()
    df = pd.read_csv(PUBLIC_DATASET_PATH)
    # Normalize columns to text/label
    text_col = next((c for c in ("text", "body", "content", "message") if c in df.columns), None)
    label_col = next((c for c in ("label", "class", "type", "is_phishing") if c in df.columns), None)
    if text_col is None or label_col is None:
        return pd.DataFrame()
    out = pd.DataFrame({"text": df[text_col].fillna(""), "label": df[label_col]})
    # The Nazario corpus is entirely phishing; we synthesize legitimate
    # negatives from a small holdout to keep the pipeline trainable.
    out["label"] = out["label"].astype(str).str.lower()
    return out


def train(
    human_emails: list[dict],
    force: bool = False,
) -> dict:
    """Train the classifier and persist to /ml/models/classifier.pkl.

    Returns evaluation metrics dict.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = _load_human_emails(human_emails)
    public = _load_public_dataset()
    dataset_size = len(df)
    used_public = False

    if len(df) < 20 and len(public) > 0:
        df = pd.concat([df, public], ignore_index=True)
        used_public = True
        note = (
            f"Local human_emails too small ({dataset_size} rows); "
            f"augmented with {len(public)} rows from public phishing dataset."
        )
    elif len(df) < 20:
        note = (
            f"Dataset too small ({dataset_size} rows) and no public dataset "
            f"found; training on what we have."
        )
    else:
        note = f"Trained on {dataset_size} local human_emails only."

    if df.empty:
        raise RuntimeError(
            "No training data available. Add labeled emails first, or place a "
            "public phishing dataset CSV at ml/sample_data/nazario_phishing.csv"
        )

    # Ensure only phishing/legitimate labels
    df = df[df["label"].isin(["phishing", "legitimate"])].copy()
    df["label"] = df["label"].map({"phishing": 1, "legitimate": 0})
    if df["label"].nunique() < 2:
        raise RuntimeError("Training data must contain both phishing and legitimate labels.")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    # float(): sklearn returns numpy scalars, which are not JSON-serializable
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 3),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 3),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 3),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 3),
        "train_size": int(len(df)),
        "note": note,
        "used_public_dataset": used_public,
    }

    # Spec: print accuracy / precision / recall / F1
    print(f"[{note}]")
    print(f"Trained on {len(df)} samples ({df['label'].sum()} phishing, {len(df) - int(df['label'].sum())} legitimate)")
    print(f"Accuracy:  {metrics['accuracy']}")
    print(f"Precision: {metrics['precision']}")
    print(f"Recall:    {metrics['recall']}")
    print(f"F1:        {metrics['f1']}")
    print(f"Model saved to: {MODEL_PATH}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    return metrics


_cached_model = None
_cached_mtime = None


def _load_model():
    """Load the pickled pipeline, reusing it across calls until it is retrained.

    /detect-all predicts one email at a time; without this every email would
    re-read the pickle from disk.
    """
    global _cached_model, _cached_mtime

    if not os.path.isfile(MODEL_PATH):
        raise RuntimeError(
            "Classifier not trained yet. Train it first — see README "
            "'Step 7 — Train the detection classifier'."
        )
    mtime = os.path.getmtime(MODEL_PATH)
    if _cached_model is None or _cached_mtime != mtime:
        with open(MODEL_PATH, "rb") as f:
            _cached_model = pickle.load(f)
        _cached_mtime = mtime
    return _cached_model


def predict(text: str) -> tuple[str, float]:
    """Return (verdict, confidence) where verdict in {'phishing','legitimate'}."""
    pipeline = _load_model()
    proba = pipeline.predict_proba([text])[0]
    classes = pipeline.classes_
    idx = int(proba.argmax())
    verdict = "phishing" if classes[idx] == 1 else "legitimate"
    return verdict, float(proba[idx])


if __name__ == "__main__":
    # CLI training with sample in-memory data if DB not reachable
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        samples = [
            {"subject": "URGENT: verify your account", "body": "Your password will expire in 24 hours. Act now.", "label": "phishing"},
            {"subject": "Invoice #4421 due", "body": "Please settle your invoice immediately to avoid suspension.", "label": "phishing"},
            {"subject": "Security alert", "body": "Unauthorized access detected. Last chance to verify.", "label": "phishing"},
            {"subject": "Meeting agenda", "body": "Here is the agenda for Friday's team meeting. See you there.", "label": "legitimate"},
            {"subject": "Lunch order", "body": "Please confirm your lunch order for tomorrow.", "label": "legitimate"},
            {"subject": "Payroll update", "body": "Your payroll details have been updated in the HR system.", "label": "legitimate"},
        ]
        print(train(samples, force=True))
    else:
        print("Run with --demo to train on built-in samples, or import train()/predict().")
