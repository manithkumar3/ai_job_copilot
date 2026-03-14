from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    flash,
    get_current_user,
    get_user_by_email,
    get_user_by_google_sub,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.templating import render_template


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.state.user = user
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render_template(request, "auth/login.html")


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        flash(request, "Invalid email or password.", "error")
        return RedirectResponse("/auth/login", status_code=303)

    login_user(request, user)
    flash(request, f"Welcome back, {user.full_name}.", "success")
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/register")
def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.state.user = user
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render_template(request, "auth/register.html")


@router.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = get_user_by_email(db, email)
    if existing:
        flash(request, "An account with that email already exists.", "error")
        return RedirectResponse("/auth/register", status_code=303)

    user = User(full_name=full_name.strip(), email=email.lower().strip(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    login_user(request, user)
    flash(request, "Your account is ready. Start by uploading your resume.", "success")
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/google")
async def google_login(request: Request):
    if not hasattr(oauth, "google"):
        flash(request, "Google login is not configured yet. Add Google credentials in your .env file.", "error")
        return RedirectResponse("/auth/login", status_code=303)

    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not hasattr(oauth, "google"):
        flash(request, "Google login is not available.", "error")
        return RedirectResponse("/auth/login", status_code=303)

    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    google_sub = user_info["sub"]
    email = user_info["email"].lower().strip()
    user = get_user_by_google_sub(db, google_sub) or get_user_by_email(db, email)
    if not user:
        user = User(full_name=user_info.get("name") or email.split("@")[0], email=email, google_sub=google_sub)
        db.add(user)
    else:
        user.google_sub = google_sub

    db.commit()
    db.refresh(user)
    login_user(request, user)
    flash(request, f"Signed in with Google as {user.full_name}.", "success")
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", status_code=303)
