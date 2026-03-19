from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, Enum):
    WISHLIST = "Wishlist"
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


class ContactTopic(str, Enum):
    FEEDBACK = "Feedback"
    QUESTION = "Question"
    GENERAL = "General"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)

    resume_versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    activities: Mapped[list["ActivityLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    contact_submissions: Mapped[list["ContactSubmission"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ResumeVersion(TimestampMixin, Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    source_filename: Mapped[str] = mapped_column(Text)
    stored_filename: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(Text)
    extracted_text: Mapped[str] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="resume_versions")
    jobs: Mapped[list["Job"]] = relationship(back_populates="resume_version")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="resume_version")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    resume_version_id: Mapped[int | None] = mapped_column(ForeignKey("resume_versions.id"), nullable=True)

    company_name: Mapped[str] = mapped_column(Text)
    job_title: Mapped[str] = mapped_column(Text)
    job_description: Mapped[str] = mapped_column(Text)
    job_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus), default=JobStatus.WISHLIST)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_applied: Mapped[date | None] = mapped_column(Date, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    prep_interview_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="jobs")
    resume_version: Mapped[ResumeVersion | None] = relationship(back_populates="jobs")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="job")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    resume_version_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    match_score: Mapped[int] = mapped_column(Integer)
    missing_skills: Mapped[str] = mapped_column(Text)
    unmet_requirements: Mapped[str] = mapped_column(Text)
    improvements: Mapped[str] = mapped_column(Text)
    ats_tips: Mapped[str] = mapped_column(Text)
    keywords_to_add: Mapped[str] = mapped_column(Text)
    rewritten_summary: Mapped[str] = mapped_column(Text)
    improved_resume_text: Mapped[str] = mapped_column(Text)
    generated_resume_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="analyses")
    resume_version: Mapped["ResumeVersion"] = relationship(back_populates="analyses")
    job: Mapped[Job | None] = relationship(back_populates="analyses")


class Reminder(TimestampMixin, Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message: Mapped[str] = mapped_column(Text)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="reminders")
    job: Mapped["Job"] = relationship(back_populates="reminders")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    action: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="activities")


class ContactSubmission(TimestampMixin, Base):
    __tablename__ = "contact_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, index=True)
    topic: Mapped[ContactTopic] = mapped_column(SqlEnum(ContactTopic), default=ContactTopic.GENERAL)
    message: Mapped[str] = mapped_column(Text)

    user: Mapped[User | None] = relationship(back_populates="contact_submissions")
