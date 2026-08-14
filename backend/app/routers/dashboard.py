"""Dashboard aggregation and export endpoints."""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    DetectionResult,
    EmailLabel,
    EmailSource,
    EvalScore,
    GeneratedEmail,
    HumanEmail,
    Scenario,
    TacticLabel,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Aggregate eval scores, tactic counts, and detection rates by source."""
    # 1) Average eval scores by source
    score_rows = (
        db.query(
            EvalScore.email_source,
            func.avg(EvalScore.readability_score),
            func.avg(EvalScore.sentiment_score),
            func.avg(EvalScore.persuasion_score),
            func.avg(EvalScore.similarity_score),
        )
        .group_by(EvalScore.email_source)
        .all()
    )
    scores = {
        row[0].value: {
            "readability_score": round(row[1] or 0, 3),
            "sentiment_score": round(row[2] or 0, 3),
            "persuasion_score": round(row[3] or 0, 3),
            "similarity_score": round(row[4] or 0, 3),
        }
        for row in score_rows
    }

    # 2) Tactic counts by source
    tactic_rows = (
        db.query(
            TacticLabel.email_source,
            TacticLabel.tactic_type,
            func.count(TacticLabel.id),
        )
        .group_by(TacticLabel.email_source, TacticLabel.tactic_type)
        .all()
    )
    tactics = {}
    for source, tactic, count in tactic_rows:
        tactics.setdefault(source.value, {})[tactic.value] = count

    # 3) Detection rates
    report = []
    for source in (EmailSource.GENERATED, EmailSource.HUMAN):
        total = (
            db.query(DetectionResult)
            .filter(DetectionResult.email_source == source)
            .count()
        )
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
                "detection_rate": round(detected / total * 100, 2) if total else 0.0,
            }
        )

    # 4) All emails joined with scores for the table view
    emails = []
    for source, model in (
        (EmailSource.GENERATED, GeneratedEmail),
        (EmailSource.HUMAN, HumanEmail),
    ):
        for email in db.query(model).all():
            score = (
                db.query(EvalScore)
                .filter_by(email_id=email.id, email_source=source)
                .first()
            )
            scenario_type = None
            if source == EmailSource.GENERATED:
                scenario = db.get(Scenario, email.scenario_id)
                scenario_type = scenario.type.value if scenario else None
            emails.append(
                {
                    "id": email.id,
                    "source": source.value,
                    "scenario_type": scenario_type,
                    "subject": email.subject,
                    "readability_score": score.readability_score if score else None,
                    "sentiment_score": score.sentiment_score if score else None,
                    "persuasion_score": score.persuasion_score if score else None,
                    "similarity_score": score.similarity_score if score else None,
                }
            )

    return {"scores": scores, "tactics": tactics, "detection": report, "emails": emails}


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """Export the full dataset as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "source",
            "scenario_type",
            "subject",
            "readability_score",
            "sentiment_score",
            "persuasion_score",
            "similarity_score",
            "classifier_verdict",
        ]
    )

    for source, model in (
        (EmailSource.GENERATED, GeneratedEmail),
        (EmailSource.HUMAN, HumanEmail),
    ):
        for email in db.query(model).all():
            score = (
                db.query(EvalScore)
                .filter_by(email_id=email.id, email_source=source)
                .first()
            )
            detection = (
                db.query(DetectionResult)
                .filter_by(email_id=email.id, email_source=source)
                .first()
            )
            scenario_type = None
            if source == EmailSource.GENERATED:
                scenario = db.get(Scenario, email.scenario_id)
                scenario_type = scenario.type.value if scenario else None
            writer.writerow(
                [
                    email.id,
                    source.value,
                    scenario_type or "",
                    email.subject,
                    score.readability_score if score else "",
                    score.sentiment_score if score else "",
                    score.persuasion_score if score else "",
                    score.similarity_score if score else "",
                    detection.classifier_verdict.value if detection else "",
                ]
            )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=emails_export.csv"},
    )


@router.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db)):
    """Export a summary report as PDF (via reportlab)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    summary = dashboard_summary(db)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Phishing Simulation &amp; Benchmarking — Summary Report", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Scores table
    story.append(Paragraph("Average Evaluation Scores by Source", styles["Heading2"]))
    score_data = [["Metric", "Generated", "Human"]]
    metrics = ["readability_score", "sentiment_score", "persuasion_score", "similarity_score"]
    for m in metrics:
        score_data.append(
            [
                m,
                str(summary["scores"].get("generated", {}).get(m, "-")),
                str(summary["scores"].get("human", {}).get(m, "-")),
            ]
        )
    table = Table(score_data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 16))

    # Detection table
    story.append(Paragraph("Detection Rates", styles["Heading2"]))
    det_data = [["Source", "Total", "Detected", "Rate (%)"]]
    for row in summary["detection"]:
        det_data.append(
            [row["email_source"], row["total"], row["detected"], row["detection_rate"]]
        )
    det_table = Table(det_data)
    det_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(det_table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=summary_report.pdf"},
    )
