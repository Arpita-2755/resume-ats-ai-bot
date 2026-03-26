from __future__ import annotations

from pathlib import Path

from .ats_engine import ATSAnalysis, analyze_resume_against_jd
from .resume_rewriter import rewrite_resume
from .templates import export_resume_file


def run_ats_pipeline(
    jd_text: str,
    resume_text: str,
    template: str = "classic",
    output_format: str = "docx",
    output_dir: str | Path = "outputs",
) -> tuple[ATSAnalysis, str, Path]:
    analysis = analyze_resume_against_jd(jd_text, resume_text)
    improved_resume_text = rewrite_resume(resume_text, jd_text, analysis=analysis)
    file_path = export_resume_file(
        resume_text=improved_resume_text,
        style=template,
        output_format=output_format,
        output_dir=Path(output_dir),
    )
    return analysis, improved_resume_text, file_path

