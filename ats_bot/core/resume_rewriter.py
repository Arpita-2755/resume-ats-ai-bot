from __future__ import annotations

import itertools
import re

from .ats_engine import analyze_resume_against_jd
from .ai_mode import rewrite_resume_with_ai_if_available
from .models import ATSAnalysis
from .resume_parser import parse_resume_text, resume_data_to_text

ACTION_VERBS = [
    "Built",
    "Designed",
    "Developed",
    "Implemented",
    "Managed",
    "Optimized",
    "Improved",
    "Led",
    "Automated",
]


def rewrite_resume(
    resume_text: str,
    jd_text: str,
    analysis: ATSAnalysis | None = None,
) -> str:
    analysis = analysis or analyze_resume_against_jd(jd_text, resume_text)
    ai_rewrite = rewrite_resume_with_ai_if_available(jd_text, resume_text, analysis)
    if ai_rewrite:
        return ai_rewrite

    data = parse_resume_text(resume_text)
    missing_keywords = analysis.missing_keywords[:10]
    keyword_cycle = itertools.cycle(missing_keywords) if missing_keywords else None

    role = _guess_role(jd_text)
    key_strengths = analysis.matched_keywords[:3] or ["backend systems", "API development"]
    summary_line = (
        f"Results-driven {role} with hands-on experience in {', '.join(key_strengths)} "
        "and delivering measurable business impact."
    )
    data.sections["summary"] = [summary_line]

    for section_name in {"experience", "projects"}:
        lines = data.sections.get(section_name, [])
        if not lines:
            continue
        updated = []
        for line in lines:
            keyword = next(keyword_cycle) if keyword_cycle else None
            updated.append(_improve_bullet(line, keyword))
        data.sections[section_name] = updated

    if not data.sections.get("experience") and data.sections.get("projects"):
        data.sections["experience"] = data.sections["projects"][:2]

    skills_lines = data.sections.get("skills", [])
    merged_skills = _merge_skills(skills_lines, analysis.matched_keywords, missing_keywords)
    if merged_skills:
        data.sections["skills"] = [", ".join(merged_skills)]

    if "projects" not in data.sections:
        data.sections["projects"] = [
            "- Built a role-aligned project showcasing practical use of key JD technologies."
        ]

    return resume_data_to_text(data)


def _guess_role(jd_text: str) -> str:
    patterns = [
        r"(?:hiring|seeking|looking for)\s+(?:an?\s+)?([a-zA-Z0-9\-/\s]+?)(?:\s+with|\s+who|\s+to|[.,\n])",
        r"(?:position|role)\s*:\s*([a-zA-Z0-9\-/\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, jd_text.lower())
        if match:
            role = re.sub(r"\s+", " ", match.group(1)).strip()
            return role.title()
    return "Software Professional"


def _improve_bullet(line: str, keyword: str | None) -> str:
    cleaned = line.strip().lstrip("-*\u2022").strip()
    if not cleaned:
        return "- Led a high-impact initiative aligned with business goals."

    words = cleaned.split()
    first_word = re.sub(r"[^A-Za-z]", "", words[0]).lower() if words else ""
    action_lookup = {verb.lower() for verb in ACTION_VERBS}
    if first_word not in action_lookup:
        cleaned = f"{ACTION_VERBS[hash(cleaned) % len(ACTION_VERBS)]} {cleaned[0].lower() + cleaned[1:]}"
    else:
        cleaned = cleaned[0].upper() + cleaned[1:]

    if keyword and keyword.lower() not in cleaned.lower():
        cleaned += f" while leveraging {keyword}"
    if not re.search(r"\b\d+(?:\.\d+)?%?\b", cleaned):
        cleaned += " (add measurable impact, e.g., +25% performance)"

    return f"- {cleaned}"


def _merge_skills(existing_skill_lines: list[str], matched: list[str], missing: list[str]) -> list[str]:
    raw = ", ".join(existing_skill_lines)
    current = {skill.strip() for skill in re.split(r"[,\n|]", raw) if skill.strip()}
    additions = matched[:6] + missing[:6]
    for skill in additions:
        if len(current) >= 18:
            break
        current.add(skill)
    return sorted(current, key=lambda x: x.lower())
