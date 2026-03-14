from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import ActivityLog, Job, JobStatus, Reminder, ResumeVersion, User  # noqa: E402


SAMPLE_RESUME = """
Mani Kumar
Backend Engineer

Summary
Backend-focused software engineer with experience building APIs, automation workflows, internal tools,
and data-backed web applications using Python, FastAPI, PostgreSQL, Docker, and cloud services.

Skills
Python, FastAPI, SQLAlchemy, PostgreSQL, Docker, REST API, HTML, CSS, Git, Linux

Experience
- Built internal platforms that reduced manual operations and improved reporting visibility.
- Delivered production-ready APIs with authentication, structured data models, and clean service layers.
- Collaborated with product and design teams to ship user-friendly workflow tools.
""".strip()


def main() -> None:
    init_db()
    uploads_dir = ROOT / "app" / "static" / "uploads" / "resumes"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == "demo@example.com").first()
        if existing:
            print("Demo data already exists.")
            return

        user = User(full_name="Demo User", email="demo@example.com", password_hash=hash_password("password123"))
        db.add(user)
        db.commit()
        db.refresh(user)

        resume_path = uploads_dir / "demo_resume.txt"
        resume_path.write_text(SAMPLE_RESUME, encoding="utf-8")
        resume = ResumeVersion(
            user_id=user.id,
            name="Backend Resume v1",
            source_filename="demo_resume.txt",
            stored_filename="demo_resume.txt",
            file_path=str(resume_path),
            extracted_text=SAMPLE_RESUME,
            ai_summary="Backend-focused software engineer with FastAPI and PostgreSQL experience.",
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

        jobs = [
            Job(
                user_id=user.id,
                resume_version_id=resume.id,
                company_name="Acme Labs",
                job_title="Backend Engineer",
                job_description="We need a Backend Engineer with Python, FastAPI, PostgreSQL, Docker, AWS, and API design experience. Remote role. Full-time.",
                location="Remote",
                status=JobStatus.APPLIED,
                tags="Remote, Urgent",
                is_bookmarked=True,
                date_applied=date.today() - timedelta(days=9),
                required_skills="Python, FastAPI, PostgreSQL, Docker, AWS",
                experience_level="3+ Years",
                employment_type="Full-Time",
                priority=5,
            ),
            Job(
                user_id=user.id,
                company_name="Northstar Systems",
                job_title="Platform Engineer",
                job_description="Looking for platform engineering experience with Docker, Kubernetes, CI/CD, PostgreSQL, and cloud infrastructure.",
                location="Bangalore",
                status=JobStatus.WISHLIST,
                tags="Dream Company",
                required_skills="Docker, Kubernetes, PostgreSQL, CI/CD",
                experience_level="Senior",
                employment_type="Full-Time",
                priority=4,
            ),
            Job(
                user_id=user.id,
                company_name="BrightHire",
                job_title="Software Engineer",
                job_description="Build and maintain web APIs with Python, SQL, and cloud services. Hybrid role.",
                location="Chennai",
                status=JobStatus.INTERVIEW,
                tags="Hybrid",
                required_skills="Python, SQL, AWS",
                experience_level="Mid Level",
                employment_type="Full-Time",
                priority=3,
            ),
        ]
        db.add_all(jobs)
        db.commit()

        reminder = Reminder(
            user_id=user.id,
            job_id=jobs[0].id,
            remind_at=datetime.now() + timedelta(days=1),
            message="Send a short follow-up email to the recruiter",
        )
        db.add(reminder)
        db.add(ActivityLog(user_id=user.id, action="Seeded demo data", details="Created sample user, jobs, and resume"))
        db.commit()
        print("Demo data created. Login with demo@example.com / password123")


if __name__ == "__main__":
    main()

