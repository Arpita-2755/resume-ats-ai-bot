from __future__ import annotations

import io
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ats_bot.bots.common import format_analysis_text
from ats_bot.config import settings
from ats_bot.core.ats_engine import analyze_resume_against_jd
from ats_bot.core.parsers import parse_text_from_bytes
from ats_bot.core.resume_rewriter import rewrite_resume
from ats_bot.core.templates import export_resume_file

WAITING_JD, WAITING_RESUME = range(2)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text(
        "Send /ats to start ATS scoring.\n"
        "Step 1: send JD text/file (.txt/.pdf/.doc/.docx)\n"
        "Step 2: send resume file/text\n"
        "Then choose one of 3 CV templates to download the fixed resume."
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text("Bot is live. Send /ats to begin.")


async def ats_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Send the Job Description (text or file).")
    return WAITING_JD


async def handle_jd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    jd_text = await _extract_text_from_message(message, context)
    if not jd_text:
        await message.reply_text("Could not read JD. Send plain text or a valid file.")
        return WAITING_JD

    context.user_data["jd_text"] = jd_text
    await message.reply_text("Great. Now send the resume (text or file).")
    return WAITING_RESUME


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    resume_text = await _extract_text_from_message(message, context)
    if not resume_text:
        await message.reply_text("Could not read resume. Send plain text or a valid file.")
        return WAITING_RESUME

    jd_text = context.user_data.get("jd_text")
    if not jd_text:
        await message.reply_text("JD is missing. Send /ats and start again.")
        return ConversationHandler.END

    output_format = "docx"
    if message.document and message.document.file_name:
        extension = Path(message.document.file_name).suffix.lower()
        if extension == ".pdf":
            output_format = "pdf"
    context.user_data["output_format"] = output_format

    analysis = analyze_resume_against_jd(jd_text, resume_text)
    improved_resume = rewrite_resume(resume_text, jd_text, analysis=analysis)
    context.user_data["analysis"] = analysis.to_dict()
    context.user_data["improved_resume"] = improved_resume

    await message.reply_text(format_analysis_text(analysis))
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Classic", callback_data="tpl:classic"),
                InlineKeyboardButton("Modern", callback_data="tpl:modern"),
                InlineKeyboardButton("Minimal", callback_data="tpl:minimal"),
            ]
        ]
    )
    await message.reply_text("Choose a template to generate the fixed resume:", reply_markup=keyboard)
    return ConversationHandler.END


async def handle_template_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    payload = query.data.split(":", maxsplit=1)
    style = payload[1] if len(payload) > 1 else "classic"
    improved_resume = context.user_data.get("improved_resume")

    if not improved_resume:
        await query.message.reply_text("No analyzed resume found. Send /ats first.")
        return

    primary_format = context.user_data.get("output_format", "docx")
    if primary_format not in {"docx", "pdf"}:
        primary_format = "docx"
    secondary_format = "pdf" if primary_format == "docx" else "docx"

    generated_files = []
    try:
        for output_format in [primary_format, secondary_format]:
            output_file = export_resume_file(
                resume_text=improved_resume,
                style=style,
                output_format=output_format,
                output_dir=settings.output_dir,
                base_filename=f"telegram_{query.from_user.id}",
            )
            generated_files.append(output_file)
            with output_file.open("rb") as file_handle:
                await query.message.reply_document(
                    document=InputFile(file_handle, filename=output_file.name),
                    caption=f"Fixed resume ({output_format.upper()}) with {style.title()} template.",
                )
    finally:
        for generated_file in generated_files:
            generated_file.unlink(missing_ok=True)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Send /ats when you're ready.")
    return ConversationHandler.END


async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message:
        await update.message.reply_text(
            "Send /ats to start ATS scoring.\n"
            "Flow: JD first, then Resume, then choose template."
        )


async def _extract_text_from_message(message, context: ContextTypes.DEFAULT_TYPE) -> str:
    if message.document:
        tg_file = await context.bot.get_file(message.document.file_id)
        buffer = io.BytesIO()
        await tg_file.download_to_memory(out=buffer)
        filename = message.document.file_name or "uploaded.txt"
        try:
            return parse_text_from_bytes(filename, buffer.getvalue())
        except Exception:
            return ""
    if message.text and not message.text.startswith("/"):
        return message.text.strip()
    return ""


def run_telegram_bot() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment.")

    logging.basicConfig(
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        level=logging.INFO,
    )
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    conversation = ConversationHandler(
        entry_points=[CommandHandler("ats", ats_start)],
        states={
            WAITING_JD: [MessageHandler(filters.TEXT | filters.Document.ALL, handle_jd)],
            WAITING_RESUME: [
                MessageHandler(filters.TEXT | filters.Document.ALL, handle_resume)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(conversation)
    application.add_handler(CallbackQueryHandler(handle_template_choice, pattern=r"^tpl:"))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, fallback_message))
    logger.info("Telegram bot polling started.")
    application.run_polling()
