import re
from collections import Counter
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


KNOWN_SKILLS = [
    "python",
    "fastapi",
    "django",
    "flask",
    "postgresql",
    "mysql",
    "sql",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "react",
    "javascript",
    "typescript",
    "html",
    "css",
    "rest api",
    "graphql",
    "redis",
    "celery",
    "machine learning",
    "llm",
    "openai",
    "git",
    "linux",
]


def fetch_url_text(url: str) -> str:
    with httpx.Client(timeout=10, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = " ".join(soup.stripped_strings)
    return f"{title}\n{text}".strip()


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = [skill.title() for skill in KNOWN_SKILLS if skill in lowered]
    unique_sorted = sorted(set(found))
    return unique_sorted[:15]


def guess_company_and_title(text: str, url: str | None = None) -> tuple[str, str]:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if " - " in first_line:
        left, right = first_line.split(" - ", 1)
        if len(left.split()) <= 6:
            return right.strip()[:80], left.strip()[:120]
    if " at " in text[:300].lower():
        match = re.search(r"(?P<title>[A-Z][^\n]{2,80}) at (?P<company>[A-Z][A-Za-z0-9 &.-]{2,80})", text[:500])
        if match:
            return match.group("company").strip(), match.group("title").strip()
    if url:
        host = urlparse(url).netloc.replace("www.", "")
        parts = host.split(".")
        if parts:
            company = parts[0].replace("-", " ").title()
            return company, first_line[:120] or "Open Role"
    return "Unknown Company", first_line[:120] or "Open Role"


def guess_location(text: str) -> str | None:
    patterns = [
        r"(Remote(?:\s*-\s*\w+)?)",
        r"Location[:\s]+([A-Za-z ,]+)",
        r"(Bengaluru|Bangalore|Chennai|Hyderabad|Pune|Mumbai|Delhi|New York|San Francisco|London|Remote)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def guess_employment_type(text: str) -> str | None:
    lowered = text.lower()
    for label in ["full-time", "part-time", "contract", "internship", "freelance"]:
        if label in lowered:
            return label.title()
    return None


def guess_experience_level(text: str) -> str | None:
    lowered = text.lower()
    for label in ["entry level", "junior", "mid level", "senior", "lead", "manager"]:
        if label in lowered:
            return label.title()
    match = re.search(r"(\d+\+?\s+years)", lowered)
    if match:
        return match.group(1).title()
    return None


def extract_job_data(job_description: str = "", job_url: str | None = None) -> dict[str, str]:
    source_text = job_description.strip()
    if not source_text and job_url:
        try:
            source_text = fetch_url_text(job_url)
        except Exception:
            source_text = ""

    company_name, job_title = guess_company_and_title(source_text, job_url)
    skills = extract_skills(source_text)
    keyword_counts = Counter(word for word in re.findall(r"[A-Za-z][A-Za-z+#.]{2,}", source_text))
    top_keywords = [word for word, _count in keyword_counts.most_common(20)]

    return {
        "company_name": company_name,
        "job_title": job_title,
        "job_description": source_text,
        "job_link": job_url or "",
        "location": guess_location(source_text) or "",
        "required_skills": ", ".join(skills),
        "experience_level": guess_experience_level(source_text) or "",
        "employment_type": guess_employment_type(source_text) or "",
        "notes": "",
        "top_keywords": ", ".join(top_keywords[:10]),
    }

