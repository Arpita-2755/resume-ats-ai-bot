from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal

from .models import ATSAnalysis

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger(__name__)


def is_ai_mode_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def get_ai_mode_label() -> str:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return "Heuristic (no AI key)"
    provider, model = _resolve_provider_and_model()
    if OpenAI is None:
        return f"Configured {provider}:{model} (openai package missing)"
    return f"AI {provider}:{model}"


def enhance_analysis_if_available(
    jd_text: str,
    resume_text: str,
    analysis: ATSAnalysis,
) -> ATSAnalysis:
    if not is_ai_mode_available():
        return analysis

    user_prompt = (
        "You are improving ATS feedback quality.\n"
        "Given JD, resume text, and current heuristic analysis, return strict JSON only with keys:\n"
        "strengths (max 4), improvements (max 5), missing_keywords (max 12).\n"
        "Keep suggestions concrete and ATS-oriented.\n\n"
        f"JD:\n{jd_text}\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Current analysis JSON:\n{json.dumps(analysis.to_dict(), ensure_ascii=True)}"
    )
    output_text = _run_llm(
        system_prompt="Return only valid JSON. No markdown.",
        user_prompt=user_prompt,
        max_output_tokens=550,
    )
    if not output_text:
        return analysis

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


def rewrite_resume_with_ai_if_available(
    jd_text: str,
    resume_text: str,
    analysis: ATSAnalysis,
) -> str | None:
    if not is_ai_mode_available():
        return None

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
    rewritten = _run_llm(
        system_prompt="Return only the rewritten resume text.",
        user_prompt=user_prompt,
        max_output_tokens=1500,
    )
    if not rewritten or len(rewritten.strip()) < 120:
        return None
    return rewritten.strip()


def _run_llm(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> str | None:
    client, provider, model = _get_client_provider_model()
    if client is None:
        return None

    try:
        if provider == "openrouter":
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_output_tokens,
                temperature=0.2,
            )
            return _extract_chat_content(completion)

        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=max_output_tokens,
        )
        return (response.output_text or "").strip() or None
    except Exception as exc:  # pragma: no cover
        logger.warning("AI provider call failed, using heuristic fallback: %s", exc)
        return None


def _get_client_provider_model() -> tuple[OpenAI | None, Literal["openai", "openrouter"], str]:
    if OpenAI is None:
        return None, "openai", ""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "openai", ""

    provider, model = _resolve_provider_and_model()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()

    if provider == "openrouter":
        headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "resume-ats-ai-bot"),
        }
        client = OpenAI(api_key=api_key, base_url=base_url, default_headers=headers)
    else:
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

    return client, provider, model


def _resolve_provider_and_model() -> tuple[Literal["openai", "openrouter"], str]:
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    provider: Literal["openai", "openrouter"] = "openrouter" if "openrouter.ai" in base_url else "openai"
    default_model = "openai/gpt-4o-mini" if provider == "openrouter" else "gpt-5.4"
    model = os.getenv("OPENAI_MODEL", default_model).strip() or default_model
    return provider, model


def _extract_chat_content(completion) -> str | None:
    try:
        content = completion.choices[0].message.content
    except Exception:
        return None
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        chunks = []
        for item in content:
            text = ""
            if isinstance(item, dict):
                text = str(item.get("text", ""))
            else:
                text = str(getattr(item, "text", "") or "")
            if text:
                chunks.append(text)
        joined = "\n".join(chunks).strip()
        return joined or None
    return None


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
