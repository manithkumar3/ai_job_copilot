from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import flash, get_current_user
from app.database import get_db
from app.models import Job, JobStatus, Reminder, ResumeVersion
from app.services.ai import best_resume_for_job, clear_job_prep, generate_job_prep, load_cached_job_prep, store_job_prep
from app.services.analytics import add_activity
from app.services.job_extractor import extract_job_data
from app.templating import render_template


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _require_user(request: Request, db: Session):
    user = get_current_user(request, db)
    request.state.user = user
    if not user:
        return None, RedirectResponse("/auth/login", status_code=303)
    return user, None


@router.get("")
def list_jobs(
    request: Request,
    q: str = "",
    status: str = "",
    sort: str = "newest",
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    query = select(Job).where(Job.user_id == user.id)
    if q:
        like = f"%{q}%"
        query = query.where(
            or_(
                Job.company_name.ilike(like),
                Job.job_title.ilike(like),
                Job.job_description.ilike(like),
                Job.notes.ilike(like),
                Job.tags.ilike(like),
                Job.location.ilike(like),
            )
        )
    if status and status in JobStatus._value2member_map_:
        query = query.where(Job.status == JobStatus(status))

    if sort == "company":
        query = query.order_by(Job.company_name.asc())
    elif sort == "priority":
        query = query.order_by(Job.priority.desc(), Job.created_at.desc())
    else:
        query = query.order_by(Job.created_at.desc())

    jobs = db.execute(query).scalars().all()
    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.created_at.desc())).scalars().all()
    return render_template(request, "jobs/list.html", {"jobs": jobs, "resumes": resumes, "statuses": list(JobStatus)})


@router.get("/new")
def new_job(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.created_at.desc())).scalars().all()
    return render_template(
        request,
        "jobs/form.html",
        {"job": None, "statuses": list(JobStatus), "resumes": resumes, "prefill": {}, "suggested_resume_id": None, "resume_scores": []},
    )


@router.get("/{job_id}/edit")
def edit_job(request: Request, job_id: int, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        flash(request, "Job not found.", "error")
        return RedirectResponse("/jobs", status_code=303)
    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.created_at.desc())).scalars().all()
    return render_template(
        request,
        "jobs/form.html",
        {"job": job, "statuses": list(JobStatus), "resumes": resumes, "prefill": {}, "suggested_resume_id": job.resume_version_id, "resume_scores": []},
    )


@router.post("/extract")
def extract_job_prefill(
    request: Request,
    job_description: str = Form(""),
    job_link: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    prefill = extract_job_data(job_description=job_description, job_url=job_link or None)
    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id)).scalars().all()
    suggested_resume_id, resume_scores = best_resume_for_job(resumes, prefill.get("job_description", ""))
    flash(request, "We extracted what we could from the description or link. Review and edit anything before saving.", "success")
    return render_template(
        request,
        "jobs/form.html",
        {"job": None, "statuses": list(JobStatus), "resumes": resumes, "prefill": prefill, "suggested_resume_id": suggested_resume_id, "resume_scores": resume_scores},
    )


@router.post("/save")
def save_job(
    request: Request,
    company_name: str = Form(...),
    job_title: str = Form(...),
    job_description: str = Form(...),
    job_link: str = Form(""),
    location: str = Form(""),
    salary: str = Form(""),
    status: str = Form(JobStatus.WISHLIST.value),
    notes: str = Form(""),
    date_applied: str = Form(""),
    contact_person: str = Form(""),
    resume_version_id: str = Form(""),
    required_skills: str = Form(""),
    experience_level: str = Form(""),
    employment_type: str = Form(""),
    tags: str = Form(""),
    priority: int = Form(0),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    applied_date = date.fromisoformat(date_applied) if date_applied else None
    resume_id = int(resume_version_id) if resume_version_id else None
    job = Job(
        user_id=user.id,
        company_name=company_name.strip(),
        job_title=job_title.strip(),
        job_description=job_description.strip(),
        job_link=job_link.strip() or None,
        location=location.strip() or None,
        salary=salary.strip() or None,
        status=JobStatus(status),
        notes=notes.strip() or None,
        date_applied=applied_date,
        contact_person=contact_person.strip() or None,
        resume_version_id=resume_id,
        required_skills=required_skills.strip() or None,
        experience_level=experience_level.strip() or None,
        employment_type=employment_type.strip() or None,
        tags=tags.strip() or None,
        priority=priority,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    add_activity(db, user.id, "Saved job", f"{job.job_title} at {job.company_name}", job.id)
    flash(request, "Job saved to your tracker.", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@router.post("/{job_id}/update")
def update_job(
    request: Request,
    job_id: int,
    company_name: str = Form(...),
    job_title: str = Form(...),
    job_description: str = Form(...),
    job_link: str = Form(""),
    location: str = Form(""),
    salary: str = Form(""),
    status: str = Form(JobStatus.WISHLIST.value),
    notes: str = Form(""),
    date_applied: str = Form(""),
    contact_person: str = Form(""),
    resume_version_id: str = Form(""),
    required_skills: str = Form(""),
    experience_level: str = Form(""),
    employment_type: str = Form(""),
    tags: str = Form(""),
    priority: int = Form(0),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        flash(request, "Job not found.", "error")
        return RedirectResponse("/jobs", status_code=303)

    clear_job_prep(job)
    job.company_name = company_name.strip()
    job.job_title = job_title.strip()
    job.job_description = job_description.strip()
    job.job_link = job_link.strip() or None
    job.location = location.strip() or None
    job.salary = salary.strip() or None
    job.status = JobStatus(status)
    job.notes = notes.strip() or None
    job.date_applied = date.fromisoformat(date_applied) if date_applied else None
    job.contact_person = contact_person.strip() or None
    job.resume_version_id = int(resume_version_id) if resume_version_id else None
    job.required_skills = required_skills.strip() or None
    job.experience_level = experience_level.strip() or None
    job.employment_type = employment_type.strip() or None
    job.tags = tags.strip() or None
    job.priority = priority
    db.commit()
    add_activity(db, user.id, "Updated job", f"{job.job_title} at {job.company_name}", job.id)
    flash(request, "Job updated.", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@router.get("/{job_id}")
def job_detail(request: Request, job_id: int, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        flash(request, "Job not found.", "error")
        return RedirectResponse("/jobs", status_code=303)

    reminders = sorted(job.reminders, key=lambda item: item.remind_at)
    analyses = sorted(job.analyses, key=lambda item: item.created_at, reverse=True)
    latest_resume = job.resume_version
    if not latest_resume:
        latest_resume = (
            db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.created_at.desc()))
            .scalars()
            .first()
        )
    job_prep = load_cached_job_prep(job)
    if not job_prep:
        generated_prep = generate_job_prep(
            job_description=job.job_description,
            job_title=job.job_title,
            company_name=job.company_name,
            resume_text=latest_resume.extracted_text if latest_resume else "",
        )
        job_prep = store_job_prep(job, generated_prep)
        db.commit()
    return render_template(
        request,
        "jobs/detail.html",
        {"job": job, "reminders": reminders, "analyses": analyses, "job_prep": job_prep},
    )

@router.post("/{job_id}/status")
def update_status(
    request: Request,
    job_id: int,
    status: str = Form(...),
    next_url: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        return RedirectResponse("/jobs", status_code=303)
    job.status = JobStatus(status)
    if job.status == JobStatus.APPLIED and not job.date_applied:
        job.date_applied = date.today()
    db.commit()
    add_activity(db, user.id, "Updated status", f"{job.job_title} moved to {job.status.value}", job.id)
    flash(request, "Job status updated.", "success")
    return RedirectResponse(next_url or f"/jobs/{job.id}", status_code=303)


@router.post("/{job_id}/reminders")
def add_reminder(
    request: Request,
    job_id: int,
    remind_at: str = Form(...),
    message: str = Form(...),
    next_url: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        return RedirectResponse("/jobs", status_code=303)

    reminder = Reminder(
        user_id=user.id,
        job_id=job.id,
        remind_at=datetime.fromisoformat(remind_at),
        message=message.strip(),
    )
    db.add(reminder)
    db.commit()
    flash(request, "Reminder added.", "success")
    return RedirectResponse(next_url or f"/jobs/{job.id}", status_code=303)
