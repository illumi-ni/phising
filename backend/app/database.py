import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load .env from the project root; silent if not found (e.g. inside Docker)
dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.isfile(dotenv_path):
    load_dotenv(dotenv_path)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://phishing_user:phishing_pass@localhost:5432/phishing_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
