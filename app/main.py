from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes.auth import router as auth_router
from app.routes.jobs import router as jobs_router
from app.routes.resumes import router as resumes_router
from app.routes.web import router as web_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
    except Exception:
        logger.exception("Application startup failed while initializing the database.")
        raise
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, https_only=False, same_site="lax")

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(resumes_router)
