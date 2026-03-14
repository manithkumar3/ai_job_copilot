from collections import Counter
from datetime import date, timedelta

from app.models import ActivityLog, JobStatus


def build_dashboard_metrics(jobs: list, reminders: list) -> dict:
    total_jobs = len(jobs)
    applied_jobs = [job for job in jobs if job.status != JobStatus.WISHLIST]
    interview_jobs = [job for job in jobs if job.status == JobStatus.INTERVIEW]
    offer_jobs = [job for job in jobs if job.status == JobStatus.OFFER]

    interview_rate = round((len(interview_jobs) / max(len(applied_jobs), 1)) * 100)
    offer_rate = round((len(offer_jobs) / max(len(applied_jobs), 1)) * 100)
    status_counts = Counter(job.status.value for job in jobs)

    recent_jobs = sorted(jobs, key=lambda job: job.updated_at or job.created_at, reverse=True)[:6]
    due_reminders = [reminder for reminder in reminders if not reminder.is_done]
    no_response_threshold = date.today() - timedelta(days=7)
    no_response_alerts = [
        job
        for job in jobs
        if job.status == JobStatus.APPLIED and job.date_applied and job.date_applied <= no_response_threshold
    ]

    return {
        "total_jobs": total_jobs,
        "applications_sent": len(applied_jobs),
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
        "status_counts": status_counts,
        "recent_jobs": recent_jobs,
        "due_reminders": sorted(due_reminders, key=lambda item: item.remind_at)[:6],
        "no_response_alerts": no_response_alerts[:6],
    }


def add_activity(db, user_id: int, action: str, details: str, job_id: int | None = None) -> None:
    db.add(ActivityLog(user_id=user_id, action=action, details=details, job_id=job_id))
    db.commit()
