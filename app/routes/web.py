from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActivityLog, Job, Reminder, ResumeVersion
from app.services.analytics import build_dashboard_metrics
from app.services.ai import build_job_insights
from app.templating import render_template


router = APIRouter(tags=["web"])


@router.get("/")
def landing(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.state.user = user
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render_template(request, "index.html")


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.state.user = user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    jobs = db.execute(select(Job).where(Job.user_id == user.id)).scalars().all()
    reminders = db.execute(select(Reminder).where(Reminder.user_id == user.id)).scalars().all()
    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id)).scalars().all()
    activities = db.execute(select(ActivityLog).where(ActivityLog.user_id == user.id).order_by(ActivityLog.created_at.desc())).scalars().all()
    metrics = build_dashboard_metrics(jobs, reminders)

    latest_resume = sorted(resumes, key=lambda item: item.created_at, reverse=True)[0] if resumes else None
    insights = build_job_insights(latest_resume.extracted_text if latest_resume else "", jobs)

    return render_template(
        request,
        "dashboard/index.html",
        {
            "metrics": metrics,
            "resumes": resumes,
            "latest_resume": latest_resume,
            "insights": insights,
            "activities": activities[:8],
            "today": datetime.now(),
        },
    )


@router.get("/mock-interview")
def mock_interview_preview(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.state.user = user
    return render_template(request, "mock_interview.html")
