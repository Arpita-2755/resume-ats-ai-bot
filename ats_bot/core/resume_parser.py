from __future__ import annotations

import re
from collections import OrderedDict

from .models import ResumeData

SECTION_ALIASES = {
    "summary": {"summary", "professional summary", "profile", "objective"},
    "experience": {"experience", "work experience", "employment", "work history"},
    "projects": {"projects", "project experience"},
    "skills": {"skills", "technical skills", "core skills", "competencies"},
    "education": {"education", "academic background"},
    "certifications": {"certifications", "certificates"},
}


def parse_resume_text(resume_text: str) -> ResumeData:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return ResumeData(name="Candidate Name", email=None, phone=None, links=[], sections={})

    name = lines[0]
    email = _extract_first(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
    phone = _extract_first(
        r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}",
        resume_text,
    )
    links = re.findall(r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+", resume_text)

    sections: OrderedDict[str, list[str]] = OrderedDict(
        (name, []) for name in SECTION_ALIASES.keys()
    )
    sections["other"] = []

    current_section = "summary"
    for idx, line in enumerate(lines[1:], start=1):
        canonical = _canonical_section(line)
        if canonical:
            current_section = canonical
            continue
        if _is_contact_line(line):
            continue
        sections[current_section].append(line)

    cleaned_sections = {section: items for section, items in sections.items() if items}
    if "summary" not in cleaned_sections and len(lines) > 2:
        fallback_summary = []
        for line in lines[1:]:
            if _canonical_section(line):
                break
            if _is_contact_line(line):
                continue
            fallback_summary.append(line)
            if len(fallback_summary) == 2:
                break
        if fallback_summary:
            cleaned_sections["summary"] = fallback_summary

    return ResumeData(
        name=name,
        email=email.group(0) if email else None,
        phone=phone.group(0) if phone else None,
        links=links[:3],
        sections=cleaned_sections,
    )


def resume_data_to_text(data: ResumeData) -> str:
    output_lines: list[str] = [data.name]
    contact = []
    if data.email:
        contact.append(data.email)
    if data.phone:
        contact.append(data.phone)
    if data.links:
        contact.extend(data.links)
    if contact:
        output_lines.append(" | ".join(contact))
        output_lines.append("")

    for section, items in data.sections.items():
        output_lines.append(section.title())
        for item in items:
            if item.startswith(("-", "*", "\u2022")):
                output_lines.append(item)
            else:
                output_lines.append(f"- {item}")
        output_lines.append("")

    return "\n".join(output_lines).strip()


def _extract_first(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text)


def _canonical_section(line: str) -> str | None:
    clean = re.sub(r"[^a-zA-Z\s]", "", line).strip().lower()
    for canonical, variants in SECTION_ALIASES.items():
        if clean in variants:
            return canonical
    return None


def _is_contact_line(line: str) -> bool:
    if "@" in line:
        return True
    if "linkedin.com" in line.lower() or "github.com" in line.lower():
        return True
    return bool(re.search(r"\d{6,}", re.sub(r"\D", "", line)))
