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

SKILL_ALIASES = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js", "node.js", "nodejs"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "reactjs"],
    "angular": ["angular"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "spring boot": ["spring boot", "springboot"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "mssql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "docker": ["docker", "containerization", "container"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "cicd", "jenkins", "github actions"],
    "rest api": ["rest", "rest api", "restful api"],
    "graphql": ["graphql"],
    "machine learning": ["machine learning", "ml"],
    "nlp": ["nlp", "natural language processing"],
}


def analyze_resume_against_jd(jd_text: str, resume_text: str) -> ATSAnalysis:
    jd_keywords = extract_keywords(jd_text, limit=40)
    resume_tokens = set(tokenize_words(resume_text))

    matched_keywords = [kw for kw in jd_keywords if kw in resume_tokens]
    missing_keywords = [kw for kw in jd_keywords if kw not in resume_tokens]
    keyword_coverage = len(matched_keywords) / max(1, len(jd_keywords))

    required_skills = _extract_required_skills(jd_text)
    matched_skills = [skill for skill in required_skills if _contains_skill(resume_text, skill)]
    missing_skills = [skill for skill in required_skills if skill not in matched_skills]
    skill_coverage = len(matched_skills) / max(1, len(required_skills))

    priority_phrases = _extract_priority_phrases(jd_text)
    phrase_hits = [phrase for phrase in priority_phrases if _phrase_in_text(phrase, resume_text)]
    phrase_coverage = len(phrase_hits) / max(1, len(priority_phrases))

    section_hits = _count_section_hits(resume_text)
    structure_score = min(1.0, section_hits / 4.0)

    action_hits = sum(1 for token in resume_tokens if token in ACTION_VERBS)
    quantified_hits = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", resume_text))
    impact_score = min(0.5, action_hits / 6.0 * 0.5) + min(0.5, quantified_hits / 4.0 * 0.5)

    keyword_score = min(4.0, keyword_coverage * 4.0)
    skill_score = min(2.0, skill_coverage * 2.0)
    phrase_score = min(2.0, phrase_coverage * 2.0)
    total = round(keyword_score + skill_score + phrase_score + structure_score + impact_score, 1)
    total = max(0.0, min(10.0, total))

    final_matched = _unique_preserving_order(matched_skills + matched_keywords)
    final_missing = _unique_preserving_order(missing_skills + missing_keywords)

    strengths, improvements = _build_feedback(
        total=total,
        keyword_coverage=keyword_coverage,
        skill_coverage=skill_coverage,
        phrase_coverage=phrase_coverage,
        section_hits=section_hits,
        action_hits=action_hits,
        quantified_hits=quantified_hits,
        matched_keywords=final_matched,
        missing_keywords=final_missing,
        missing_skills=missing_skills,
    )

    return ATSAnalysis(
        score=total,
        keyword_coverage=round(keyword_coverage, 2),
        breakdown={
            "keyword_alignment": round(keyword_score, 2),
            "skill_alignment": round(skill_score, 2),
            "jd_phrase_alignment": round(phrase_score, 2),
            "structure": round(structure_score, 2),
            "impact_evidence": round(impact_score, 2),
        },
        matched_keywords=final_matched[:18],
        missing_keywords=final_missing[:18],
        strengths=strengths,
        improvements=improvements,
    )


def _extract_required_skills(jd_text: str) -> list[str]:
    lower_jd = normalize_text(jd_text)
    required = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(alias in lower_jd for alias in aliases):
            required.append(canonical)
    return required


def _contains_skill(text: str, canonical_skill: str) -> bool:
    lower_text = normalize_text(text)
    return any(alias in lower_text for alias in SKILL_ALIASES.get(canonical_skill, [canonical_skill]))


def _extract_priority_phrases(jd_text: str, limit: int = 10) -> list[str]:
    lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(
            marker in lower
            for marker in [
                "must",
                "required",
                "responsible",
                "hands-on",
                "experience with",
                "proficient",
                "strong",
            ]
        ):
            cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", lower)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned and len(cleaned.split()) >= 3:
                selected.append(" ".join(cleaned.split()[:6]))
        if len(selected) >= limit:
            break

    if not selected:
        top_keywords = extract_keywords(jd_text, limit=12)
        selected = [" ".join(top_keywords[idx : idx + 3]) for idx in range(0, len(top_keywords), 3)]

    return [phrase for phrase in selected if phrase][:limit]


def _phrase_in_text(phrase: str, text: str) -> bool:
    phrase_tokens = [token for token in tokenize_words(phrase) if len(token) > 2]
    resume_tokens = set(tokenize_words(text))
    if not phrase_tokens:
        return False
    hits = sum(1 for token in phrase_tokens if token in resume_tokens)
    return hits / len(phrase_tokens) >= 0.6


def _count_section_hits(resume_text: str) -> int:
    lower_text = normalize_text(resume_text)
    return sum(
        1
        for section_variants in SECTION_SIGNALS.values()
        if any(variant in lower_text for variant in section_variants)
    )


def _build_feedback(
    total: float,
    keyword_coverage: float,
    skill_coverage: float,
    phrase_coverage: float,
    section_hits: int,
    action_hits: int,
    quantified_hits: int,
    matched_keywords: list[str],
    missing_keywords: list[str],
    missing_skills: list[str],
) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    improvements: list[str] = []

    if keyword_coverage >= 0.6:
        strengths.append("Good keyword alignment with the JD.")
    if skill_coverage >= 0.65:
        strengths.append("Most required technical skills are present.")
    if phrase_coverage >= 0.5:
        strengths.append("Experience statements align with JD responsibilities.")
    if quantified_hits >= 4:
        strengths.append("Includes measurable outcomes (numbers/percentages).")
    if matched_keywords:
        strengths.append("Strong matches: " + ", ".join(matched_keywords[:6]))

    if missing_skills:
        improvements.append("Add missing required skills explicitly: " + ", ".join(missing_skills[:6]))
    if keyword_coverage < 0.55 and missing_keywords:
        improvements.append(
            "Inject these JD terms naturally into Summary/Experience/Projects: "
            + ", ".join(missing_keywords[:8])
        )
    if section_hits < 4:
        improvements.append("Use ATS-friendly headings: Summary, Experience, Skills, Education, Projects.")
    if action_hits < 4:
        improvements.append("Start bullets with strong action verbs (Built, Led, Improved, Optimized).")
    if quantified_hits < 3:
        improvements.append("Add quantified impact in bullets (%, time saved, revenue, users).")
    if total < 7:
        improvements.append("Tailor top 4 bullets directly to JD requirements and required tools.")

    if not improvements:
        improvements.append("Fine-tune phrasing and ordering of achievements to match JD priorities.")
    if not strengths:
        strengths.append("Base resume structure exists; tighter JD alignment will raise ATS score.")
    return strengths, improvements


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output

