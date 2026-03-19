from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.auth import pop_flashes
from app.config import get_settings


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def nl2list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip("- ").strip() for part in value.splitlines() if part.strip()]


templates.env.filters["split_csv"] = split_csv
templates.env.filters["nl2list"] = nl2list
templates.env.globals["now"] = datetime.utcnow


def render_template(request: Request, template_name: str, context: dict[str, Any] | None = None):
    settings = get_settings()
    site_url = settings.base_url.rstrip("/")
    canonical_path = request.url.path if request.url.path.startswith("/") else f"/{request.url.path}"
    canonical_url = f"{site_url}{canonical_path}"

    base_context = {
        "request": request,
        "current_user": getattr(request.state, "user", None),
        "flashes": pop_flashes(request),
        "active_path": request.url.path,
        "seo_site_name": settings.app_name,
        "seo_description": "AI Job Copilot helps job seekers track applications, manage resumes, prepare for interviews, and improve their job search with AI-powered insights.",
        "seo_canonical_url": canonical_url,
        "seo_image_url": f"{site_url}/static/img/logo.png",
        "seo_robots": "noindex, nofollow" if settings.debug else "index, follow",
        "seo_base_url": site_url,
    }
    if context:
        base_context.update(context)
    return templates.TemplateResponse(template_name, base_context)
