import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class ScenarioType(str, enum.Enum):
    PASSWORD_RESET = "password_reset"
    INVOICE = "invoice"
    IT_ALERT = "it_alert"


class EmailLabel(str, enum.Enum):
    PHISHING = "phishing"
    LEGITIMATE = "legitimate"


class EmailSource(str, enum.Enum):
    GENERATED = "generated"
    HUMAN = "human"


class TacticType(str, enum.Enum):
    URGENCY = "urgency"
    AUTHORITY = "authority"
    SCARCITY = "scarcity"
    FEAR = "fear"
    CURIOSITY = "curiosity"
    OTHER = "other"


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(ScenarioType), nullable=False)
    tone = Column(String(255), nullable=False)
    urgency_level = Column(Integer, nullable=False)  # 1–5
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    generated_emails = relationship("GeneratedEmail", back_populates="scenario")

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, type={self.type}, urgency={self.urgency_level})>"


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    model_used = Column(String(255), nullable=False)
    prompt_used = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    scenario = relationship("Scenario", back_populates="generated_emails")

    def __repr__(self) -> str:
        return f"<GeneratedEmail(id={self.id}, scenario={self.scenario_id})>"


class HumanEmail(Base):
    __tablename__ = "human_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    label = Column(Enum(EmailLabel), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<HumanEmail(id={self.id}, label={self.label})>"


class TacticLabel(Base):
    __tablename__ = "tactic_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, nullable=False)       # no strict FK
    email_source = Column(Enum(EmailSource), nullable=False)
    tactic_type = Column(Enum(TacticType), nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TacticLabel(id={self.id}, tactic={self.tactic_type}, conf={self.confidence})>"


class EvalScore(Base):
    __tablename__ = "eval_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, nullable=False)       # no strict FK
    email_source = Column(Enum(EmailSource), nullable=False)
    readability_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    persuasion_score = Column(Float, nullable=False)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<EvalScore(id={self.id}, readability={self.readability_score})>"


class DetectionResult(Base):
    __tablename__ = "detection_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, nullable=False)       # no strict FK
    email_source = Column(Enum(EmailSource), nullable=False)
    classifier_verdict = Column(Enum(EmailLabel), nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<DetectionResult(id={self.id}, verdict={self.classifier_verdict})>"
