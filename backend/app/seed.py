"""Seed the database with 3 sample phishing scenarios."""

from .database import SessionLocal
from .models import Scenario, ScenarioType


def seed_scenarios() -> list[Scenario]:
    scenarios = [
        Scenario(
            type=ScenarioType.PASSWORD_RESET,
            tone="urgent and official",
            urgency_level=5,
        ),
        Scenario(
            type=ScenarioType.INVOICE,
            tone="professional with mild urgency",
            urgency_level=3,
        ),
        Scenario(
            type=ScenarioType.IT_ALERT,
            tone="alarming and technical",
            urgency_level=4,
        ),
    ]

    db = SessionLocal()
    try:
        # Only insert if table is empty
        if db.query(Scenario).count() == 0:
            db.add_all(scenarios)
            db.commit()
            for s in scenarios:
                db.refresh(s)
            print(f"✅ Seeded {len(scenarios)} scenarios.")
        else:
            print("ℹ️  scenarios table already has data; skipping seed.")
        return scenarios
    except Exception as exc:
        db.rollback()
        print(f"❌ Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_scenarios()
