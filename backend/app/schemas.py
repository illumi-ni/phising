from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import EmailLabel, EmailSource, ScenarioType, TacticType


# ──────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────

class ScenarioCreate(BaseModel):
    type: ScenarioType
    tone: str = Field(min_length=1, max_length=255)
    urgency_level: int = Field(ge=1, le=5)


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ScenarioType
    tone: str
    urgency_level: int
    created_at: datetime


# ──────────────────────────────────────────────
# Generated emails
# ──────────────────────────────────────────────

class GeneratedEmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    subject: str
    body: str
    model_used: str
    prompt_used: str
    created_at: datetime


# ──────────────────────────────────────────────
# Human emails
# ──────────────────────────────────────────────

class HumanEmailCreate(BaseModel):
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    source: str = Field(min_length=1)
    label: EmailLabel


class HumanEmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    body: str
    source: str
    label: EmailLabel
    created_at: datetime


# ──────────────────────────────────────────────
# Tactic labels / eval scores / detection
# ──────────────────────────────────────────────

class TacticLabelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    email_source: EmailSource
    tactic_type: TacticType
    confidence: float
    created_at: datetime


class EvalScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    email_source: EmailSource
    readability_score: float
    sentiment_score: float
    persuasion_score: float
    similarity_score: float
    created_at: datetime


class DetectionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    email_source: EmailSource
    classifier_verdict: EmailLabel
    confidence: float
    created_at: datetime
