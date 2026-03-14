from typing import Any

from fastapi import Request
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def login_user(request: Request, user: User) -> None:
    if "session" not in request.scope:
        return
    request.session["user_id"] = user.id


def logout_user(request: Request) -> None:
    if "session" not in request.scope:
        return
    request.session.clear()


def get_current_user(request: Request, db: Session) -> User | None:
    session = request.scope.get("session")
    if session is None:
        return None
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.lower().strip())).scalar_one_or_none()


def get_user_by_google_sub(db: Session, google_sub: str) -> User | None:
    return db.execute(select(User).where(User.google_sub == google_sub)).scalar_one_or_none()


def flash(request: Request, message: str, category: str = "info") -> None:
    if "session" not in request.scope:
        return
    messages = request.session.setdefault("_flashes", [])
    messages.append({"message": message, "category": category})
    request.session["_flashes"] = messages


def pop_flashes(request: Request) -> list[dict[str, Any]]:
    if "session" not in request.scope:
        return []
    flashes = request.session.pop("_flashes", [])
    seen: set[tuple[str, str]] = set()
    unique_flashes: list[dict[str, Any]] = []
    for item in flashes:
        key = (item.get("category", "info"), item.get("message", ""))
        if key in seen:
            continue
        seen.add(key)
        unique_flashes.append(item)
    return unique_flashes
