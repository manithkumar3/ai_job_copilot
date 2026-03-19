from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, get_db
from app.models import ContactSubmission, ContactTopic
from app.routes.web import router


def create_contact_test_client(tmp_path):
    database_path = tmp_path / "contact-test.db"
    engine = create_engine(f"sqlite:///{database_path}", future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), session_factory


def test_contact_submission_is_saved(tmp_path):
    client, session_factory = create_contact_test_client(tmp_path)

    response = client.post(
        "/contact",
        data={
            "name": "Manith Rai",
            "email": "manithkumar3@gmail.com",
            "topic": ContactTopic.FEEDBACK.value,
            "message": "The dashboard is helpful and I would like an admin panel later.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/contact"

    with session_factory() as db:
        saved = db.execute(select(ContactSubmission)).scalar_one()

    assert saved.name == "Manith Rai"
    assert saved.email == "manithkumar3@gmail.com"
    assert saved.topic == ContactTopic.FEEDBACK
    assert "admin panel" in saved.message
