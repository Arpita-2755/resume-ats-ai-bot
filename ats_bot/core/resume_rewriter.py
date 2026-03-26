from __future__ import annotations

import itertools
import re

from .ats_engine import analyze_resume_against_jd
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
    data = parse_resume_text(resume_text)
    missing_keywords = analysis.missing_keywords[:10]
    keyword_cycle = itertools.cycle(missing_keywords) if missing_keywords else None

    for section_name, lines in list(data.sections.items()):
        if section_name in {"experience", "projects"}:
            updated: list[str] = []
            for line in lines:
                keyword = next(keyword_cycle) if keyword_cycle else None
                updated.append(_improve_bullet(line, keyword))
            data.sections[section_name] = updated

    skills_lines = data.sections.get("skills", [])
    skills_blob = " ".join(skills_lines).lower()
    missing_for_skills = [kw for kw in missing_keywords if kw not in skills_blob][:8]
    if missing_for_skills:
        if skills_lines:
            skills_lines.append("Targeted JD Keywords: " + ", ".join(missing_for_skills))
        else:
            skills_lines = ["Targeted JD Keywords: " + ", ".join(missing_for_skills)]
        data.sections["skills"] = skills_lines

    summary_lines = data.sections.get("summary", [])
    summary_text = " ".join(summary_lines).lower()
    summary_additions = [kw for kw in missing_keywords[:3] if kw not in summary_text]
    if summary_additions:
        sentence = "Focused on " + ", ".join(summary_additions) + " aligned to role expectations."
        summary_lines.append(sentence)
        data.sections["summary"] = summary_lines

    return resume_data_to_text(data)


def _improve_bullet(line: str, keyword: str | None) -> str:
    cleaned = line.strip().lstrip("-*\u2022").strip()
    if not cleaned:
        return "- Led a key initiative aligned to business goals."

    words = cleaned.split()
    first_word = re.sub(r"[^A-Za-z]", "", words[0]).lower() if words else ""
    action_lookup = {verb.lower() for verb in ACTION_VERBS}
    if first_word not in action_lookup:
        cleaned = f"{ACTION_VERBS[hash(cleaned) % len(ACTION_VERBS)]} {cleaned[0].lower() + cleaned[1:]}"
    else:
        cleaned = cleaned[0].upper() + cleaned[1:]

    if keyword and keyword.lower() not in cleaned.lower():
        cleaned += f" using {keyword}"
    if not re.search(r"\b\d+(?:\.\d+)?%?\b", cleaned):
        cleaned += "; impact: [add measurable result]"

    return f"- {cleaned}"
