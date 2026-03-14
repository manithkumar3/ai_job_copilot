from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings


settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    ensure_db_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()


def ensure_schema_updates() -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
    pending_statements = []
    if "prep_interview_questions" not in existing_columns:
        pending_statements.append("ALTER TABLE jobs ADD COLUMN prep_interview_questions TEXT")
    if "prep_cover_letter" not in existing_columns:
        pending_statements.append("ALTER TABLE jobs ADD COLUMN prep_cover_letter TEXT")
    if "prep_provider" not in existing_columns:
        pending_statements.append("ALTER TABLE jobs ADD COLUMN prep_provider TEXT")
    if "prep_generated_at" not in existing_columns:
        pending_statements.append("ALTER TABLE jobs ADD COLUMN prep_generated_at TIMESTAMP")

    if not pending_statements:
        return

    with engine.begin() as connection:
        for statement in pending_statements:
            connection.execute(text(statement))


@lru_cache(maxsize=1)
def ensure_db_initialized() -> bool:
    init_db()
    return True
