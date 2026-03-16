from collections import Counter
from datetime import date, datetime, timedelta

from app.models import ActivityLog, JobStatus

STATUS_ORDER = [
    JobStatus.WISHLIST,
    JobStatus.APPLIED,
    JobStatus.INTERVIEW,
    JobStatus.OFFER,
    JobStatus.REJECTED,
]

STATUS_COLORS = {
    JobStatus.WISHLIST.value: "#9eb1a7",
    JobStatus.APPLIED.value: "#1d7a5f",
    JobStatus.INTERVIEW.value: "#f0a66f",
    JobStatus.OFFER.value: "#68ce97",
    JobStatus.REJECTED.value: "#d15656",
}


def _to_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _build_weekly_series(items: list, attr_name: str, length: int = 6) -> dict:
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    week_starts = [current_week_start - timedelta(weeks=offset) for offset in range(length - 1, -1, -1)]
    counts = {week_start: 0 for week_start in week_starts}

    for item in items:
        item_date = _to_date(getattr(item, attr_name, None))
        if item_date is None:
            continue
        week_start = item_date - timedelta(days=item_date.weekday())
        if week_start in counts:
            counts[week_start] += 1

    points = []
    max_value = max(counts.values(), default=0)
    for week_start in week_starts:
        week_end = week_start + timedelta(days=6)
        value = counts[week_start]
        points.append(
            {
                "label": week_start.strftime("%b %d"),
                "range": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                "value": value,
                "height": max(16, round((value / max(max_value, 1)) * 100)) if value else 16,
            }
        )

    return {
        "points": points,
        "max_value": max_value,
        "total": sum(counts.values()),
    }


def _build_status_chart(status_counts: Counter, total_jobs: int) -> dict:
    segments = []
    legend = []
    start = 0

    for status in STATUS_ORDER:
        label = status.value
        count = status_counts.get(label, 0)
        if total_jobs:
            share = round((count / total_jobs) * 100, 1)
        else:
            share = 0

        if count:
            end = start + (count / total_jobs) * 100 if total_jobs else start
            segments.append(f"{STATUS_COLORS[label]} {start:.2f}% {end:.2f}%")
            start = end

        legend.append(
            {
                "label": label,
                "count": count,
                "share": share,
                "color": STATUS_COLORS[label],
            }
        )

    gradient = ", ".join(segments) if segments else "#dce9da 0 100%"
    return {"gradient": gradient, "legend": legend}


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
    jobs_added_series = _build_weekly_series(jobs, "created_at")
    applications_series = _build_weekly_series(applied_jobs, "date_applied")
    status_chart = _build_status_chart(status_counts, total_jobs)

    return {
        "total_jobs": total_jobs,
        "applications_sent": len(applied_jobs),
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
        "status_counts": status_counts,
        "status_chart": status_chart,
        "jobs_added_series": jobs_added_series,
        "applications_series": applications_series,
        "recent_jobs": recent_jobs,
        "due_reminders": sorted(due_reminders, key=lambda item: item.remind_at)[:6],
        "no_response_alerts": no_response_alerts[:6],
    }


def add_activity(db, user_id: int, action: str, details: str, job_id: int | None = None) -> None:
    db.add(ActivityLog(user_id=user_id, action=action, details=details, job_id=job_id))
    db.commit()
