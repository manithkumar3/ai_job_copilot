import json
import re
from collections import Counter
from datetime import datetime, timezone

from app.config import get_settings
from app.services.job_extractor import KNOWN_SKILLS, extract_skills

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


def _normalize_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}", text.lower()))
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "you",
        "your",
        "from",
        "that",
        "this",
        "will",
        "have",
        "has",
        "our",
        "are",
        "job",
        "role",
        "team",
        "work",
        "using",
    }
    return {token for token in tokens if token not in stopwords}


def _line_gaps(job_description: str, resume_text: str) -> list[str]:
    resume_tokens = _normalize_tokens(resume_text)
    gaps = []
    for line in job_description.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        line_tokens = _normalize_tokens(clean_line)
        if line_tokens and len(line_tokens & resume_tokens) / max(len(line_tokens), 1) < 0.2:
            gaps.append(clean_line[:160])
    return gaps[:5]


def _default_analysis(resume_text: str, job_description: str, job_title: str = "", company_name: str = "") -> dict:
    resume_tokens = _normalize_tokens(resume_text)
    jd_tokens = _normalize_tokens(job_description)
    overlap = resume_tokens & jd_tokens

    jd_skills = set(skill.lower() for skill in extract_skills(job_description))
    resume_skills = set(skill.lower() for skill in extract_skills(resume_text))
    missing_skills = sorted(skill.title() for skill in jd_skills - resume_skills)

    score_base = 40 + int((len(overlap) / max(len(jd_tokens), 1)) * 45) + min(len(resume_skills & jd_skills) * 4, 15)
    match_score = max(25, min(score_base, 96))

    frequent_terms = Counter(
        token for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.]{2,}", job_description.lower()) if token in KNOWN_SKILLS
    )
    keywords_to_add = [term.title() for term, _count in frequent_terms.most_common(8) if term not in resume_tokens]
    unmet_requirements = _line_gaps(job_description, resume_text)

    improvements = [
        "Tailor your experience bullets to emphasize measurable outcomes that match the role.",
        "Surface the most relevant tools and platforms closer to the top of the resume.",
        "Mirror important language from the job description in your summary and skills section.",
    ]
    if missing_skills:
        improvements.insert(0, f"Add evidence of {', '.join(missing_skills[:4])} if you have used them in projects or work.")

    ats_tips = [
        "Keep section headings standard: Summary, Experience, Projects, Skills, Education.",
        "Use plain formatting and avoid tables or text boxes in the resume file.",
        "Include exact job-specific keywords naturally in accomplishments and skills.",
    ]

    summary_target = f"{job_title} at {company_name}".strip(" at")
    rewritten_summary = (
        f"Results-driven candidate targeting {summary_target or 'this opportunity'}, bringing experience across "
        f"{', '.join(sorted((resume_skills & jd_skills) or resume_skills)[:5]) or 'software delivery'} with a focus on business impact, collaboration, and clean execution."
    )

    improved_resume_text = "\n\n".join(
        [
            "Professional Summary",
            rewritten_summary,
            "Keywords To Highlight",
            ", ".join(keywords_to_add or [skill.title() for skill in sorted(resume_skills)[:8]]) or "Communication, Delivery, Ownership",
            "Suggested Experience Direction",
            "\n".join(f"- {item}" for item in improvements),
        ]
    )

    return {
        "match_score": match_score,
        "missing_skills": missing_skills,
        "unmet_requirements": unmet_requirements,
        "improvements": improvements,
        "ats_tips": ats_tips,
        "keywords_to_add": keywords_to_add,
        "rewritten_summary": rewritten_summary,
        "improved_resume_text": improved_resume_text,
        "provider": "heuristic",
    }


def analyze_resume(resume_text: str, job_description: str, job_title: str = "", company_name: str = "") -> dict:
    settings = get_settings()
    fallback = _default_analysis(resume_text, job_description, job_title, company_name)
    if not settings.openai_api_key or OpenAI is None:
        return fallback

    prompt = f"""
You are an expert resume reviewer and job application coach.
Return only valid JSON with these keys:
match_score, missing_skills, unmet_requirements, improvements, ats_tips, keywords_to_add, rewritten_summary, improved_resume_text.

Job title: {job_title}
Company: {company_name}

Job description:
{job_description}

Resume:
{resume_text[:14000]}
""".strip()

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        parsed = json.loads(response.output_text)
        parsed["provider"] = "openai"
        if not isinstance(parsed.get("match_score"), int):
            parsed["match_score"] = fallback["match_score"]
        return {
            "match_score": max(0, min(100, parsed.get("match_score", fallback["match_score"]))),
            "missing_skills": parsed.get("missing_skills", fallback["missing_skills"]),
            "unmet_requirements": parsed.get("unmet_requirements", fallback["unmet_requirements"]),
            "improvements": parsed.get("improvements", fallback["improvements"]),
            "ats_tips": parsed.get("ats_tips", fallback["ats_tips"]),
            "keywords_to_add": parsed.get("keywords_to_add", fallback["keywords_to_add"]),
            "rewritten_summary": parsed.get("rewritten_summary", fallback["rewritten_summary"]),
            "improved_resume_text": parsed.get("improved_resume_text", fallback["improved_resume_text"]),
            "provider": parsed.get("provider", "openai"),
        }
    except Exception:
        return fallback


def best_resume_for_job(resume_versions: list, job_description: str) -> tuple[int | None, list[dict]]:
    scored = []
    for version in resume_versions:
        analysis = _default_analysis(version.extracted_text, job_description)
        scored.append({"resume_id": version.id, "name": version.name, "score": analysis["match_score"]})
    scored.sort(key=lambda item: item["score"], reverse=True)
    top = scored[0]["resume_id"] if scored else None
    return top, scored


def build_job_insights(resume_text: str, jobs: list) -> dict:
    if not jobs:
        return {
            "best_matching_jobs": [],
            "skills_to_learn": [],
            "role_trends": [],
            "suggested_titles": [],
        }

    scored_jobs = []
    skill_counter = Counter()
    title_counter = Counter()
    location_counter = Counter()

    for job in jobs:
        analysis = _default_analysis(resume_text, job.job_description, job.job_title, job.company_name)
        scored_jobs.append(
            {
                "job_id": job.id,
                "title": job.job_title,
                "company": job.company_name,
                "score": analysis["match_score"],
                "status": job.status.value,
            }
        )
        for skill in extract_skills(job.job_description):
            skill_counter[skill] += 1
        title_counter[job.job_title] += 1
        if job.location:
            location_counter[job.location] += 1

    resume_skills = {skill.lower() for skill in extract_skills(resume_text)}
    missing = [skill for skill, _count in skill_counter.most_common() if skill.lower() not in resume_skills]

    best_matching_jobs = sorted(scored_jobs, key=lambda item: item["score"], reverse=True)[:5]
    role_trends = [f"{title} ({count} roles saved)" for title, count in title_counter.most_common(5)]
    if location_counter:
        role_trends.extend(f"Location focus: {location} ({count})" for location, count in location_counter.most_common(2))

    title_words = Counter()
    for title in title_counter:
        for token in title.split():
            if len(token) > 3:
                title_words[token.title()] += 1
    suggested_titles = [title for title, _count in title_counter.most_common(4)]
    if not suggested_titles:
        suggested_titles = [f"{word} Engineer" for word, _count in title_words.most_common(4)]

    return {
        "best_matching_jobs": best_matching_jobs,
        "skills_to_learn": missing[:8],
        "role_trends": role_trends[:6],
        "suggested_titles": suggested_titles[:6],
    }


def _default_job_prep(job_description: str, job_title: str = "", company_name: str = "", resume_text: str = "") -> dict:
    skills = extract_skills(job_description)[:6]
    company_label = company_name or "the company"
    role_label = job_title or "this role"
    resume_skills = extract_skills(resume_text)[:5] if resume_text else []

    questions = [
        f"How does your past experience prepare you for the {role_label} position?",
        f"Why do you want to join {company_label}?",
        f"Which projects best demonstrate your fit for this job?",
        f"How do you prioritize tasks when multiple deadlines compete?",
    ]
    for skill in skills[:4]:
        questions.append(f"Can you describe a time you used {skill} to solve a practical problem?")

    cover_letter = (
        f"Dear Hiring Team,\n\n"
        f"I am excited to apply for the {role_label} role at {company_label}. "
        f"My background includes experience building and improving software solutions, and I am especially interested in this role because it aligns with my strengths in "
        f"{', '.join(resume_skills or skills[:3] or ['problem solving', 'collaboration', 'delivery'])}. "
        f"I enjoy working on meaningful product challenges, collaborating across teams, and turning requirements into reliable results.\n\n"
        f"What stands out to me about this opportunity is the focus on "
        f"{', '.join(skills[:3]) if skills else 'delivering strong technical outcomes'}."
        f" I would welcome the chance to contribute with a practical, ownership-driven approach while continuing to grow with your team.\n\n"
        f"Thank you for your time and consideration. I would be glad to discuss how my experience can support {company_label}'s goals.\n\n"
        f"Sincerely,\nYour Name"
    )

    return {"interview_questions": questions[:8], "cover_letter": cover_letter, "provider": "heuristic"}


def generate_job_prep(job_description: str, job_title: str = "", company_name: str = "", resume_text: str = "") -> dict:
    settings = get_settings()
    fallback = _default_job_prep(job_description, job_title, company_name, resume_text)
    if not settings.openai_api_key or OpenAI is None:
        return fallback

    prompt = f"""
You are helping a job applicant prepare for one saved job.
Return only valid JSON with keys: interview_questions, cover_letter.

Create:
1. 6 to 8 interview questions tailored to the role.
2. A simple professional cover letter.

Job title: {job_title}
Company: {company_name}

Job description:
{job_description}

Resume context:
{resume_text[:6000]}
""".strip()

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(model=settings.openai_model, input=prompt)
        parsed = json.loads(response.output_text)
        return {
            "interview_questions": parsed.get("interview_questions", fallback["interview_questions"]),
            "cover_letter": parsed.get("cover_letter", fallback["cover_letter"]),
            "provider": "openai",
        }
    except Exception:
        return fallback


def load_cached_job_prep(job) -> dict | None:
    if not job.prep_interview_questions or not job.prep_cover_letter:
        return None

    try:
        interview_questions = json.loads(job.prep_interview_questions)
    except Exception:
        interview_questions = []

    if not isinstance(interview_questions, list):
        interview_questions = []

    return {
        "interview_questions": [str(question) for question in interview_questions if str(question).strip()],
        "cover_letter": job.prep_cover_letter,
        "provider": job.prep_provider or "cached",
    }


def store_job_prep(job, prep: dict) -> dict:
    normalized = {
        "interview_questions": [str(question) for question in prep.get("interview_questions", []) if str(question).strip()],
        "cover_letter": str(prep.get("cover_letter", "")).strip(),
        "provider": str(prep.get("provider", "heuristic")).strip() or "heuristic",
    }
    job.prep_interview_questions = json.dumps(normalized["interview_questions"])
    job.prep_cover_letter = normalized["cover_letter"]
    job.prep_provider = normalized["provider"]
    job.prep_generated_at = datetime.now(timezone.utc)
    return normalized


def clear_job_prep(job) -> None:
    job.prep_interview_questions = None
    job.prep_cover_letter = None
    job.prep_provider = None
    job.prep_generated_at = None
