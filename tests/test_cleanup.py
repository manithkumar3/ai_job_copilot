from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import ActivityLog, Job, JobStatus, Reminder, ResumeAnalysis, ResumeVersion, User
from app.services.cleanup import delete_job, delete_resume_version


def create_session(tmp_path) -> Session:
    database_path = tmp_path / "cleanup-test.db"
    engine = create_engine(f"sqlite:///{database_path}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_factory()


def test_delete_resume_version_removes_files_analyses_and_unlinks_jobs(tmp_path):
    db = create_session(tmp_path)
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    resume_file = uploads_dir / "resume.pdf"
    generated_file = uploads_dir / "tailored.docx"
    resume_file.write_text("resume")
    generated_file.write_text("generated")

    user = User(email="resume@example.com", full_name="Resume User", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    resume = ResumeVersion(
        user_id=user.id,
        name="Backend Resume",
        source_filename="resume.pdf",
        stored_filename="resume.pdf",
        file_path=str(resume_file),
        extracted_text="FastAPI resume text",
        ai_summary="Summary",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    job = Job(
        user_id=user.id,
        company_name="Acme",
        job_title="Backend Engineer",
        job_description="FastAPI role",
        status=JobStatus.APPLIED,
        resume_version_id=resume.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    analysis = ResumeAnalysis(
        user_id=user.id,
        resume_version_id=resume.id,
        job_id=job.id,
        match_score=88,
        missing_skills="AWS",
        unmet_requirements="",
        improvements="",
        ats_tips="",
        keywords_to_add="FastAPI",
        rewritten_summary="Updated summary",
        improved_resume_text="Improved resume",
        generated_resume_path=str(generated_file),
    )
    db.add(analysis)
    db.commit()

    summary = delete_resume_version(db, resume)
    db.commit()
    db.refresh(job)

    assert summary == {"deleted_analyses": 1, "unlinked_jobs": 1}
    assert db.get(ResumeVersion, resume.id) is None
    assert db.get(ResumeAnalysis, analysis.id) is None
    assert job.resume_version_id is None
    assert not resume_file.exists()
    assert not generated_file.exists()


def test_delete_job_removes_related_rows_and_preserves_activity_history(tmp_path):
    db = create_session(tmp_path)
    generated_file = tmp_path / "generated.docx"
    generated_file.write_text("generated")

    user = User(email="jobs@example.com", full_name="Jobs User", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    resume = ResumeVersion(
        user_id=user.id,
        name="Product Resume",
        source_filename="resume.pdf",
        stored_filename="resume.pdf",
        file_path=str(tmp_path / "resume.pdf"),
        extracted_text="Resume text",
        ai_summary="Summary",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    job = Job(
        user_id=user.id,
        company_name="Northwind",
        job_title="Product Engineer",
        job_description="Build features",
        status=JobStatus.INTERVIEW,
        resume_version_id=resume.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    reminder = Reminder(user_id=user.id, job_id=job.id, message="Follow up", remind_at=datetime(2026, 3, 19, 10, 0, 0))
    analysis = ResumeAnalysis(
        user_id=user.id,
        resume_version_id=resume.id,
        job_id=job.id,
        match_score=92,
        missing_skills="",
        unmet_requirements="",
        improvements="",
        ats_tips="",
        keywords_to_add="",
        rewritten_summary="Updated summary",
        improved_resume_text="Improved resume",
        generated_resume_path=str(generated_file),
    )
    activity = ActivityLog(user_id=user.id, job_id=job.id, action="Saved job", details="Product Engineer at Northwind")
    db.add_all([reminder, analysis, activity])
    db.commit()
    db.refresh(activity)

    summary = delete_job(db, job)
    db.commit()
    db.refresh(activity)

    assert summary == {"deleted_analyses": 1, "deleted_reminders": 1, "updated_activities": 1}
    assert db.get(Job, job.id) is None
    assert db.get(Reminder, reminder.id) is None
    assert db.get(ResumeAnalysis, analysis.id) is None
    assert activity.job_id is None
    assert not generated_file.exists()
