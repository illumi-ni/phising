from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GeneratedEmail, Scenario
from ..schemas import GeneratedEmailOut, ScenarioCreate, ScenarioOut
from ..services.llm_generator import generate_email

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("", response_model=ScenarioOut, status_code=201)
def create_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    """Create a new phishing scenario."""
    scenario = Scenario(
        type=payload.type,
        tone=payload.tone,
        urgency_level=payload.urgency_level,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("", response_model=list[ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)):
    """List all scenarios, most recent first."""
    return (
        db.query(Scenario)
        .order_by(Scenario.created_at.desc(), Scenario.id.desc())
        .all()
    )


@router.post("/{scenario_id}/generate", response_model=GeneratedEmailOut)
def generate_scenario_email(scenario_id: int, db: Session = Depends(get_db)):
    """Trigger LLM generation for a scenario and persist the email."""
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = generate_email(scenario)

    email = GeneratedEmail(
        scenario_id=scenario.id,
        subject=result["subject"],
        body=result["body"],
        model_used=result["model_used"],
        prompt_used=result["prompt_used"],
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email
