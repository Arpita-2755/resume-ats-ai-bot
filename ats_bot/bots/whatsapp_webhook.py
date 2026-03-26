from __future__ import annotations

import html
import mimetypes
from pathlib import Path

import httpx
from fastapi import APIRouter, Request, Response

from ats_bot.bots.common import format_analysis_text
from ats_bot.config import settings
from ats_bot.core.ats_engine import analyze_resume_against_jd
from ats_bot.core.ai_mode import enhance_analysis_if_available
from ats_bot.core.parsers import parse_text_from_bytes

router = APIRouter(tags=["whatsapp"])


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request) -> Response:
    form = await request.form()
    body = str(form.get("Body", "")).strip()
    num_media = int(form.get("NumMedia", "0"))

    jd_text = ""
    resume_text = ""

    if num_media >= 2:
        media_entries = [
            (str(form.get(f"MediaUrl{i}", "")), str(form.get(f"MediaContentType{i}", "")))
            for i in range(num_media)
        ]
        parsed = await _download_and_parse_media(media_entries)
        if len(parsed) >= 2:
            jd_text, resume_text = parsed[0], parsed[1]
    elif body:
        jd_text, resume_text = _parse_inline_body(body)

    if not jd_text or not resume_text:
        usage = (
            "Send either:\n"
            "1) Two files in one message: JD then Resume\n"
            "or\n"
            "2) Text format:\nJD: <job description>\nRESUME: <resume text>"
        )
        return _twiml_response(usage)

    analysis = analyze_resume_against_jd(jd_text, resume_text)
    analysis = enhance_analysis_if_available(jd_text, resume_text, analysis)
    summary = format_analysis_text(analysis)
    if analysis.score < 7:
        summary += (
            "\n\nScore is low. Tip: Add missing keywords in bullets with numbers/impact."
        )

    return _twiml_response(summary[:1500])


async def _download_and_parse_media(media_entries: list[tuple[str, str]]) -> list[str]:
    auth = None
    if settings.twilio_account_sid and settings.twilio_auth_token:
        auth = (settings.twilio_account_sid, settings.twilio_auth_token)

    texts: list[str] = []
    async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
        for idx, (url, content_type) in enumerate(media_entries):
            if not url:
                continue
            response = await client.get(url)
            response.raise_for_status()
            extension = mimetypes.guess_extension(content_type or "") or ".txt"
            filename = f"upload_{idx}{extension}"
            parsed = parse_text_from_bytes(filename, response.content)
            if parsed:
                texts.append(parsed)
    return texts


def _parse_inline_body(body: str) -> tuple[str, str]:
    lower = body.lower()
    if "jd:" in lower and "resume:" in lower:
        jd_start = lower.index("jd:") + 3
        resume_start = lower.index("resume:")
        jd_text = body[jd_start:resume_start].strip()
        resume_text = body[resume_start + 7 :].strip()
        return jd_text, resume_text
    return "", ""


def _twiml_response(text: str) -> Response:
    safe_text = html.escape(text)
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{safe_text}</Message></Response>"
    )
    return Response(content=payload, media_type="application/xml")
