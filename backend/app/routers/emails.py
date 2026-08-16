"""Human email management, tactic labeling, evaluation, and detection."""
import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    DetectionResult,
    EmailLabel,
    EmailSource,
    EvalScore,
    GeneratedEmail,
    HumanEmail,
    TacticLabel,
)
from ..schemas import (
    DetectionResultOut,
    EvalScoreOut,
    HumanEmailCreate,
    HumanEmailOut,
    TacticLabelOut,
)

router = APIRouter(tags=["emails"])

REQUIRED_CSV_COLUMNS = ["subject", "body", "source", "label"]


def _get_email(db: Session, source: EmailSource, email_id: int):
    """Fetch an email by source ('generated' | 'human') and id."""
    if source == EmailSource.GENERATED:
        email = db.get(GeneratedEmail, email_id)
        if email is None:
            raise HTTPException(status_code=404, detail="Generated email not found")
        return email.subject + "\n" + email.body
    email = db.get(HumanEmail, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Human email not found")
    return email.subject + "\n" + email.body


def _reference_phishing_texts(db: Session) -> list[str]:
    """The phishing corpus every email's similarity score is measured against."""
    return [
        f"{e.subject}\n{e.body}"
        for e in db.query(HumanEmail).filter(HumanEmail.label == EmailLabel.PHISHING).all()
    ]


# ──────────────────────────────────────────────
# Human emails
# ──────────────────────────────────────────────

@router.post("/human-emails/upload")
async def upload_human_emails(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Upload a CSV of human emails. Columns: subject, body, source, label."""
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {missing}",
        )

    inserted = 0
    skipped = []
    for idx, row in df.iterrows():
        subject = str(row["subject"]).strip() if pd.notna(row["subject"]) else ""
        body = str(row["body"]).strip() if pd.notna(row["body"]) else ""
        label = str(row["label"]).strip().lower()
        if label not in (EmailLabel.PHISHING.value, EmailLabel.LEGITIMATE.value):
            skipped.append(
                {
                    "row": idx + 2,  # +2: header + 0-based index
                    "reason": f"invalid label '{row['label']}'",
                }
            )
            continue
        if not subject or not body:
            skipped.append(
                {"row": idx + 2, "reason": "empty subject or body"}
            )
            continue
        db.add(
            HumanEmail(
                subject=subject,
                body=body,
                source=str(row["source"]).strip() if pd.notna(row["source"]) else "",
                label=EmailLabel(label),
            )
        )
        inserted += 1
    db.commit()

    return {"inserted": inserted, "skipped": skipped}


@router.post("/human-emails/manual", response_model=HumanEmailOut, status_code=201)
def create_human_email(payload: HumanEmailCreate, db: Session = Depends(get_db)):
    """Insert a single human email."""
    email = HumanEmail(
        subject=payload.subject,
        body=payload.body,
        source=payload.source,
        label=payload.label,
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


@router.get("/human-emails", response_model=list[HumanEmailOut])
def list_human_emails(
    limit: int = 20, offset: int = 0, db: Session = Depends(get_db)
):
    """List human emails, paginated."""
    return (
        db.query(HumanEmail)
        .order_by(HumanEmail.created_at.desc(), HumanEmail.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ──────────────────────────────────────────────
# Tactic labeling
# ──────────────────────────────────────────────

@router.post(
    "/emails/{source}/{email_id}/label", response_model=list[TacticLabelOut]
)
def label_email(
    source: EmailSource, email_id: int, db: Session = Depends(get_db)
):
    """Run rule-based tactic labeling on one email and persist results."""
    from tactic_labeler import label_tactics

    text = _get_email(db, source, email_id)
    detected = label_tactics(text)

    # Idempotent: replace any existing tactic labels for this email
    db.query(TacticLabel).filter_by(email_id=email_id, email_source=source).delete()

    saved = []
    for t in detected:
        label = TacticLabel(
            email_id=email_id,
            email_source=source,
            tactic_type=t["tactic_type"],
            confidence=t["confidence"],
        )
        db.add(label)
        saved.append(label)
    db.commit()
    for label in saved:
        db.refresh(label)
    return saved


@router.post("/label-all")
def label_all(db: Session = Depends(get_db)):
    """Label every email that has no tactic labels yet."""
    from tactic_labeler import label_tactics

    counts = {"generated": 0, "human": 0, "tactics_created": 0}

    for source, model in (
        (EmailSource.GENERATED, GeneratedEmail),
        (EmailSource.HUMAN, HumanEmail),
    ):
        for email in db.query(model).all():
            has_labels = (
                db.query(TacticLabel)
                .filter_by(email_id=email.id, email_source=source)
                .count()
            )
            if has_labels:
                continue
            text = f"{email.subject}\n{email.body}"
            for t in label_tactics(text):
                db.add(
                    TacticLabel(
                        email_id=email.id,
                        email_source=source,
                        tactic_type=t["tactic_type"],
                        confidence=t["confidence"],
                    )
                )
                counts["tactics_created"] += 1
            counts[source.value] += 1
    db.commit()
    return counts


# ──────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────

@router.post(
    "/emails/{source}/{email_id}/evaluate", response_model=EvalScoreOut
)
def evaluate_email(
    source: EmailSource, email_id: int, db: Session = Depends(get_db)
):
    """Compute all four evaluation scores for one email and persist."""
    from evaluator import evaluate_email as compute_scores

    text = _get_email(db, source, email_id)
    ref_texts = _reference_phishing_texts(db)
    scores = compute_scores(text, ref_texts)

    # Idempotent: replace any existing scores for this email
    db.query(EvalScore).filter_by(email_id=email_id, email_source=source).delete()

    score = EvalScore(
        email_id=email_id,
        email_source=source,
        readability_score=scores["readability_score"],
        sentiment_score=scores["sentiment_score"],
        persuasion_score=scores["persuasion_score"],
        similarity_score=scores["similarity_score"],
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.post("/evaluate-all")
def evaluate_all(db: Session = Depends(get_db)):
    """Evaluate every email that has no eval_scores row yet."""
    from evaluator import evaluate_email as compute_scores

    ref_texts = _reference_phishing_texts(db)
    counts = {"generated": 0, "human": 0, "scores_created": 0}

    for source, model in (
        (EmailSource.GENERATED, GeneratedEmail),
        (EmailSource.HUMAN, HumanEmail),
    ):
        for email in db.query(model).all():
            exists = (
                db.query(EvalScore)
                .filter_by(email_id=email.id, email_source=source)
                .count()
            )
            if exists:
                continue
            text = f"{email.subject}\n{email.body}"
            scores = compute_scores(text, ref_texts)
            db.add(
                EvalScore(
                    email_id=email.id,
                    email_source=source,
                    readability_score=scores["readability_score"],
                    sentiment_score=scores["sentiment_score"],
                    persuasion_score=scores["persuasion_score"],
                    similarity_score=scores["similarity_score"],
                )
            )
            counts["scores_created"] += 1
            counts[source.value] += 1
    db.commit()
    return counts


# ──────────────────────────────────────────────
# Detection
# ──────────────────────────────────────────────

@router.post(
    "/emails/{source}/{email_id}/detect", response_model=DetectionResultOut
)
def detect_email(
    source: EmailSource, email_id: int, db: Session = Depends(get_db)
):
    """Run classifier prediction on one email and persist the result."""
    from classifier import predict

    text = _get_email(db, source, email_id)
    verdict, confidence = predict(text)

    # Idempotent: replace any existing detection result for this email
    db.query(DetectionResult).filter_by(email_id=email_id, email_source=source).delete()

    result = DetectionResult(
        email_id=email_id,
        email_source=source,
        classifier_verdict=EmailLabel(verdict),
        confidence=float(confidence),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.post("/detect-all")
def detect_all(db: Session = Depends(get_db)):
    """Detect every email that has no detection result yet."""
    from classifier import predict

    counts = {"generated": 0, "human": 0, "results_created": 0}

    for source, model in (
        (EmailSource.GENERATED, GeneratedEmail),
        (EmailSource.HUMAN, HumanEmail),
    ):
        for email in db.query(model).all():
            exists = (
                db.query(DetectionResult)
                .filter_by(email_id=email.id, email_source=source)
                .count()
            )
            if exists:
                continue
            text = f"{email.subject}\n{email.body}"
            verdict, confidence = predict(text)
            db.add(
                DetectionResult(
                    email_id=email.id,
                    email_source=source,
                    classifier_verdict=EmailLabel(verdict),
                    confidence=float(confidence),
                )
            )
            counts["results_created"] += 1
            counts[source.value] += 1
    db.commit()
    return counts


@router.get("/detection-report")
def detection_report(db: Session = Depends(get_db)):
    """Detection rate (%) per email source."""
    report = []
    for source in (EmailSource.GENERATED, EmailSource.HUMAN):
        total = (
            db.query(DetectionResult)
            .filter(DetectionResult.email_source == source)
            .count()
        )
        if total == 0:
            report.append(
                {"email_source": source.value, "total": 0, "detected": 0, "detection_rate": 0.0}
            )
            continue
        detected = (
            db.query(DetectionResult)
            .filter(
                DetectionResult.email_source == source,
                DetectionResult.classifier_verdict == EmailLabel.PHISHING,
            )
            .count()
        )
        report.append(
            {
                "email_source": source.value,
                "total": total,
                "detected": detected,
                "detection_rate": round(detected / total * 100, 2),
            }
        )
    return {"report": report}
