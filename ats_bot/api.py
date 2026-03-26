from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ats_bot.bots.whatsapp_webhook import router as whatsapp_router
from ats_bot.config import settings
from ats_bot.core.ats_engine import analyze_resume_against_jd
from ats_bot.core.parsers import parse_text_from_bytes
from ats_bot.core.resume_rewriter import rewrite_resume
from ats_bot.core.templates import TEMPLATE_STYLES, export_resume_file

app = FastAPI(title="Hackathon ATS Bot API", version="1.0.0")
app.include_router(whatsapp_router)


class AnalyzeResponse(BaseModel):
    score: float
    keyword_coverage: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    strengths: list[str]
    improvements: list[str]
    improved_resume_preview: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/templates")
def templates() -> dict:
    return {"templates": list(TEMPLATE_STYLES.keys()), "output_formats": ["docx", "pdf"]}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    jd_text: Optional[str] = Form(default=None),
    resume_text: Optional[str] = Form(default=None),
    jd_file: UploadFile | None = File(default=None),
    resume_file: UploadFile | None = File(default=None),
) -> AnalyzeResponse:
    final_jd = await _resolve_text_input(jd_text, jd_file, "JD")
    final_resume = await _resolve_text_input(resume_text, resume_file, "Resume")

    analysis = analyze_resume_against_jd(final_jd, final_resume)
    improved_resume = rewrite_resume(final_resume, final_jd, analysis=analysis)
    preview = "\n".join(improved_resume.splitlines()[:18])

    return AnalyzeResponse(
        score=analysis.score,
        keyword_coverage=analysis.keyword_coverage,
        matched_keywords=analysis.matched_keywords,
        missing_keywords=analysis.missing_keywords,
        strengths=analysis.strengths,
        improvements=analysis.improvements,
        improved_resume_preview=preview,
    )


@app.post("/fix-resume")
async def fix_resume(
    template: str = Form(default="classic"),
    output_format: str = Form(default="docx"),
    jd_text: Optional[str] = Form(default=None),
    resume_text: Optional[str] = Form(default=None),
    jd_file: UploadFile | None = File(default=None),
    resume_file: UploadFile | None = File(default=None),
):
    template = template.lower()
    output_format = output_format.lower()
    if template not in TEMPLATE_STYLES:
        raise HTTPException(status_code=400, detail="Invalid template.")
    if output_format not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="Invalid output format.")

    final_jd = await _resolve_text_input(jd_text, jd_file, "JD")
    final_resume = await _resolve_text_input(resume_text, resume_file, "Resume")

    analysis = analyze_resume_against_jd(final_jd, final_resume)
    improved_resume = rewrite_resume(final_resume, final_jd, analysis=analysis)
    output_file = export_resume_file(
        resume_text=improved_resume,
        style=template,
        output_format=output_format,
        output_dir=settings.output_dir,
        base_filename="api_resume",
    )

    media_type = (
        "application/pdf"
        if output_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=output_file,
        media_type=media_type,
        filename=Path(output_file).name,
        background=None,
    )


async def _resolve_text_input(
    plain_text: str | None,
    upload_file: UploadFile | None,
    label: str,
) -> str:
    if plain_text and plain_text.strip():
        return plain_text.strip()
    if upload_file is not None:
        content = await upload_file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"{label} file is empty.")
        try:
            return parse_text_from_bytes(upload_file.filename or f"{label.lower()}.txt", content)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse {label} file: {exc}") from exc
    raise HTTPException(status_code=400, detail=f"{label} input is required.")

