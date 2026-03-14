import json

from app.models import Job
from app.services.ai import analyze_resume
from app.services.ai import clear_job_prep, load_cached_job_prep, store_job_prep
from app.services.job_extractor import extract_job_data


def test_extract_job_data_from_text():
    result = extract_job_data(
        job_description="Backend Engineer - Acme Labs\nRemote full-time role using Python, FastAPI, PostgreSQL, Docker, and AWS."
    )
    assert result["company_name"] == "Acme Labs"
    assert result["job_title"] == "Backend Engineer"
    assert "Python" in result["required_skills"]


def test_heuristic_analysis_returns_expected_keys():
    analysis = analyze_resume(
        resume_text="Python FastAPI PostgreSQL Docker REST API",
        job_description="We need Python, FastAPI, PostgreSQL, Docker, and AWS skills.",
        job_title="Backend Engineer",
        company_name="Acme Labs",
    )
    assert 0 <= analysis["match_score"] <= 100
    assert "match_score" in analysis
    assert "missing_skills" in analysis
    assert "rewritten_summary" in analysis


def test_job_prep_cache_round_trip():
    job = Job(company_name="Acme Labs", job_title="Backend Engineer", job_description="Python FastAPI role", user_id=1)
    prep = store_job_prep(
        job,
        {
            "interview_questions": ["Tell me about a FastAPI project.", "How do you use PostgreSQL?"],
            "cover_letter": "Short cover letter",
            "provider": "heuristic",
        },
    )

    cached = load_cached_job_prep(job)

    assert prep["provider"] == "heuristic"
    assert cached is not None
    assert cached["interview_questions"] == ["Tell me about a FastAPI project.", "How do you use PostgreSQL?"]
    assert cached["cover_letter"] == "Short cover letter"
    assert json.loads(job.prep_interview_questions) == cached["interview_questions"]


def test_clear_job_prep_resets_cached_fields():
    job = Job(company_name="Acme Labs", job_title="Backend Engineer", job_description="Python FastAPI role", user_id=1)
    store_job_prep(
        job,
        {
            "interview_questions": ["Tell me about a FastAPI project."],
            "cover_letter": "Short cover letter",
            "provider": "heuristic",
        },
    )

    clear_job_prep(job)

    assert load_cached_job_prep(job) is None
    assert job.prep_generated_at is None
