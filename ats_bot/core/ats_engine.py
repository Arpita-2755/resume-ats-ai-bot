from __future__ import annotations

import re

from .models import ATSAnalysis
from .text_utils import extract_keywords, normalize_text, tokenize_words

SECTION_SIGNALS = {
    "summary": ["summary", "profile", "objective"],
    "experience": ["experience", "employment", "work history"],
    "skills": ["skills", "technical skills", "core competencies"],
    "education": ["education", "academic"],
    "projects": ["projects", "project experience"],
}

ACTION_VERBS = {
    "built",
    "designed",
    "delivered",
    "developed",
    "implemented",
    "improved",
    "increased",
    "led",
    "managed",
    "optimized",
    "reduced",
    "scaled",
    "streamlined",
    "launched",
    "automated",
    "collaborated",
    "analyzed",
}


def analyze_resume_against_jd(jd_text: str, resume_text: str) -> ATSAnalysis:
    jd_keywords = extract_keywords(jd_text, limit=35)
    resume_tokens = set(tokenize_words(resume_text))

    matched_keywords = [kw for kw in jd_keywords if kw in resume_tokens]
    missing_keywords = [kw for kw in jd_keywords if kw not in resume_tokens]

    coverage = len(matched_keywords) / max(1, len(jd_keywords))
    keyword_score = min(6.0, coverage * 6.0)

    section_hits = _count_section_hits(resume_text)
    section_score = min(2.0, (section_hits / 5.0) * 2.0)

    action_hits = sum(1 for token in resume_tokens if token in ACTION_VERBS)
    action_score = min(1.0, action_hits / 5.0)

    quantified_hits = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", resume_text))
    quant_score = min(1.0, quantified_hits / 4.0)

    total = round(keyword_score + section_score + action_score + quant_score, 1)
    total = max(0.0, min(10.0, total))

    strengths, improvements = _build_feedback(
        total=total,
        coverage=coverage,
        section_hits=section_hits,
        action_hits=action_hits,
        quantified_hits=quantified_hits,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
    )

    return ATSAnalysis(
        score=total,
        keyword_coverage=round(coverage, 2),
        matched_keywords=matched_keywords[:15],
        missing_keywords=missing_keywords[:15],
        strengths=strengths,
        improvements=improvements,
    )


def _count_section_hits(resume_text: str) -> int:
    lower_text = normalize_text(resume_text)
    hit_count = 0
    for section_variants in SECTION_SIGNALS.values():
        if any(variant in lower_text for variant in section_variants):
            hit_count += 1
    return hit_count


def _build_feedback(
    total: float,
    coverage: float,
    section_hits: int,
    action_hits: int,
    quantified_hits: int,
    matched_keywords: list[str],
    missing_keywords: list[str],
) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    improvements: list[str] = []

    if coverage >= 0.65:
        strengths.append("Good keyword overlap with the JD.")
    if section_hits >= 4:
        strengths.append("Resume has most ATS-friendly sections.")
    if quantified_hits >= 4:
        strengths.append("Includes measurable outcomes (numbers/percentages).")
    if matched_keywords:
        strengths.append(
            "Matched important keywords: " + ", ".join(matched_keywords[:6])
        )

    if coverage < 0.55 and missing_keywords:
        improvements.append(
            "Add these JD keywords naturally into experience/projects/skills: "
            + ", ".join(missing_keywords[:8])
        )
    if section_hits < 4:
        improvements.append(
            "Add clear headings: Summary, Experience, Skills, Education, Projects."
        )
    if action_hits < 4:
        improvements.append(
            "Start bullet points with strong action verbs (Built, Led, Improved, Optimized)."
        )
    if quantified_hits < 3:
        improvements.append(
            "Add metrics to achievements (e.g., reduced latency by 30%, improved CTR by 18%)."
        )
    if total < 7:
        improvements.append(
            "Tailor your summary and top 3 bullet points directly to JD requirements."
        )

    if not improvements:
        improvements.append("Fine-tune bullet points for tighter JD alignment and clarity.")
    if not strengths:
        strengths.append("Baseline structure is present; optimization can improve ATS ranking.")

    return strengths, improvements

