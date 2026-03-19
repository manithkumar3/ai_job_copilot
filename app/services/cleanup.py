from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityLog, Job, Reminder, ResumeAnalysis, ResumeVersion


def _remove_file(path_value: str | None) -> None:
    if not path_value:
        return
    Path(path_value).unlink(missing_ok=True)


def delete_resume_version(db: Session, resume: ResumeVersion) -> dict[str, int]:
    analyses = db.execute(select(ResumeAnalysis).where(ResumeAnalysis.resume_version_id == resume.id)).scalars().all()
    linked_jobs = db.execute(select(Job).where(Job.resume_version_id == resume.id)).scalars().all()

    for analysis in analyses:
        _remove_file(analysis.generated_resume_path)
        db.delete(analysis)

    for job in linked_jobs:
        job.resume_version_id = None

    _remove_file(resume.file_path)
    db.delete(resume)

    return {
        "deleted_analyses": len(analyses),
        "unlinked_jobs": len(linked_jobs),
    }


def delete_job(db: Session, job: Job) -> dict[str, int]:
    analyses = db.execute(select(ResumeAnalysis).where(ResumeAnalysis.job_id == job.id)).scalars().all()
    reminders = db.execute(select(Reminder).where(Reminder.job_id == job.id)).scalars().all()
    activities = db.execute(select(ActivityLog).where(ActivityLog.job_id == job.id)).scalars().all()

    for analysis in analyses:
        _remove_file(analysis.generated_resume_path)
        db.delete(analysis)

    for reminder in reminders:
        db.delete(reminder)

    for activity in activities:
        activity.job_id = None

    db.delete(job)

    return {
        "deleted_analyses": len(analyses),
        "deleted_reminders": len(reminders),
        "updated_activities": len(activities),
    }
