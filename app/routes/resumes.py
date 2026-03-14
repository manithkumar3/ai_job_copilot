from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import flash, get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Job, ResumeAnalysis, ResumeVersion
from app.services.ai import analyze_resume
from app.services.analytics import add_activity
from app.services.file_parser import build_docx_resume, extract_text, save_upload
from app.services.job_extractor import extract_job_data
from app.templating import render_template


router = APIRouter(prefix="/resumes", tags=["resumes"])


def _require_user(request: Request, db: Session):
    user = get_current_user(request, db)
    request.state.user = user
    if not user:
        return None, RedirectResponse("/auth/login", status_code=303)
    return user, None


@router.get("")
def list_resumes(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    resumes = db.execute(select(ResumeVersion).where(ResumeVersion.user_id == user.id).order_by(ResumeVersion.created_at.desc())).scalars().all()
    jobs = db.execute(select(Job).where(Job.user_id == user.id).order_by(Job.updated_at.desc())).scalars().all()
    analyses = db.execute(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id).order_by(ResumeAnalysis.created_at.desc())).scalars().all()
    return render_template(request, "resumes/list.html", {"resumes": resumes, "jobs": jobs, "analyses": analyses[:8]})


@router.post("/upload")
def upload_resume(
    request: Request,
    name: str = Form(...),
    resume_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    filename, file_path = save_upload(resume_file)
    try:
        extracted = extract_text(file_path)
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        flash(request, str(exc), "error")
        return RedirectResponse("/resumes", status_code=303)

    resume = ResumeVersion(
        user_id=user.id,
        name=name.strip(),
        source_filename=resume_file.filename or filename,
        stored_filename=filename,
        file_path=str(file_path),
        extracted_text=extracted,
        ai_summary=extracted[:300],
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    add_activity(db, user.id, "Uploaded resume", resume.name)
    flash(request, "Resume uploaded and parsed successfully.", "success")
    return RedirectResponse("/resumes", status_code=303)


@router.get("/{resume_id}/download")
def download_resume(request: Request, resume_id: int, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    resume = db.get(ResumeVersion, resume_id)
    if not resume or resume.user_id != user.id:
        flash(request, "Resume not found.", "error")
        return RedirectResponse("/resumes", status_code=303)
    return FileResponse(path=resume.file_path, filename=resume.source_filename)


@router.post("/analyze")
def run_analysis(
    request: Request,
    resume_version_id: int = Form(...),
    job_id: str = Form(""),
    job_description: str = Form(""),
    job_link: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    resume = db.get(ResumeVersion, resume_version_id)
    if not resume or resume.user_id != user.id:
        flash(request, "Resume not found.", "error")
        return RedirectResponse("/resumes", status_code=303)

    job = db.get(Job, int(job_id)) if job_id else None
    if job and job.user_id != user.id:
        job = None

    if job:
        job_description = job.job_description
        job_link = job.job_link or job_link
    elif job_link and not job_description.strip():
        prefill = extract_job_data(job_description="", job_url=job_link)
        job_description = prefill["job_description"]

    if not job_description.strip():
        flash(request, "Add a job description or choose a saved job first.", "error")
        return RedirectResponse("/resumes", status_code=303)

    analysis_data = analyze_resume(
        resume.extracted_text,
        job_description,
        job.job_title if job else "",
        job.company_name if job else "",
    )

    settings = get_settings()
    output_name = f"tailored_resume_{resume.id}_{job.id if job else 'custom'}.docx"
    output_path = settings.upload_dir / "generated" / output_name
    build_docx_resume(
        output_path=output_path,
        title=f"{resume.name} - Tailored Version",
        summary=analysis_data["rewritten_summary"],
        body_text=analysis_data["improved_resume_text"],
    )

    analysis = ResumeAnalysis(
        user_id=user.id,
        resume_version_id=resume.id,
        job_id=job.id if job else None,
        match_score=analysis_data["match_score"],
        missing_skills="\n".join(analysis_data["missing_skills"]),
        unmet_requirements="\n".join(analysis_data["unmet_requirements"]),
        improvements="\n".join(analysis_data["improvements"]),
        ats_tips="\n".join(analysis_data["ats_tips"]),
        keywords_to_add="\n".join(analysis_data["keywords_to_add"]),
        rewritten_summary=analysis_data["rewritten_summary"],
        improved_resume_text=analysis_data["improved_resume_text"],
        generated_resume_path=str(output_path),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    add_activity(db, user.id, "Ran resume analysis", resume.name, job.id if job else None)
    flash(request, f"Analysis complete. Match score: {analysis.match_score}%.", "success")
    return RedirectResponse(f"/resumes/analysis/{analysis.id}", status_code=303)


@router.get("/analysis/{analysis_id}")
def view_analysis(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    analysis = db.get(ResumeAnalysis, analysis_id)
    if not analysis or analysis.user_id != user.id:
        flash(request, "Analysis not found.", "error")
        return RedirectResponse("/resumes", status_code=303)
    return render_template(request, "resumes/analysis.html", {"analysis": analysis})


@router.get("/analysis/{analysis_id}/download")
def download_generated_resume(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    analysis = db.get(ResumeAnalysis, analysis_id)
    if not analysis or analysis.user_id != user.id or not analysis.generated_resume_path:
        flash(request, "Generated resume not found.", "error")
        return RedirectResponse("/resumes", status_code=303)
    filename = Path(analysis.generated_resume_path).name
    return FileResponse(path=analysis.generated_resume_path, filename=filename)
