from __future__ import annotations

import json
import logging
import os
import re

from .models import ATSAnalysis

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger(__name__)


def is_ai_mode_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def enhance_analysis_if_available(
    jd_text: str,
    resume_text: str,
    analysis: ATSAnalysis,
) -> ATSAnalysis:
    if not is_ai_mode_available():
        return analysis

    client = _get_client()
    if client is None:
        return analysis

    model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    user_prompt = (
        "You are improving ATS feedback quality.\n"
        "Given JD, resume text, and current heuristic analysis, return strict JSON only with keys:\n"
        "strengths (max 4), improvements (max 5), missing_keywords (max 12).\n"
        "Keep suggestions concrete and ATS-oriented.\n\n"
        f"JD:\n{jd_text}\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Current analysis JSON:\n{json.dumps(analysis.to_dict(), ensure_ascii=True)}"
    )
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. No markdown.",
                },
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=500,
        )
        output_text = (response.output_text or "").strip()
        parsed = _parse_json_object(output_text)
        if not parsed:
            return analysis

        return ATSAnalysis(
            score=analysis.score,
            keyword_coverage=analysis.keyword_coverage,
            breakdown=analysis.breakdown.copy(),
            matched_keywords=analysis.matched_keywords.copy(),
            missing_keywords=_limit_list(
                parsed.get("missing_keywords", analysis.missing_keywords),
                18,
            ),
            strengths=_limit_list(parsed.get("strengths", analysis.strengths), 4),
            improvements=_limit_list(parsed.get("improvements", analysis.improvements), 5),
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("AI enhancement unavailable, using heuristic output: %s", exc)
        return analysis


def rewrite_resume_with_ai_if_available(
    jd_text: str,
    resume_text: str,
    analysis: ATSAnalysis,
) -> str | None:
    if not is_ai_mode_available():
        return None

    client = _get_client()
    if client is None:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    user_prompt = (
        "Rewrite this resume for ATS alignment to the JD.\n"
        "Rules:\n"
        "1) Do not invent employers, degrees, or certifications.\n"
        "2) Keep facts from original resume; improve wording.\n"
        "3) Use headings exactly: Summary, Experience, Projects, Skills, Education.\n"
        "4) Experience/Projects must use bullets starting with strong action verbs.\n"
        "5) Add measurable placeholders only where missing, like [Add metric: 20%+].\n"
        "6) Return plain text only (no markdown fences).\n\n"
        f"JD:\n{jd_text}\n\n"
        f"Original Resume:\n{resume_text}\n\n"
        f"Current ATS analysis:\n{json.dumps(analysis.to_dict(), ensure_ascii=True)}\n"
    )
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "Return only the rewritten resume text."},
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=1400,
        )
        rewritten = (response.output_text or "").strip()
        if len(rewritten) < 120:
            return None
        return rewritten
    except Exception as exc:  # pragma: no cover
        logger.warning("AI resume rewrite unavailable, using heuristic output: %s", exc)
        return None


def _get_client() -> OpenAI | None:
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _limit_list(value, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:max_len]

