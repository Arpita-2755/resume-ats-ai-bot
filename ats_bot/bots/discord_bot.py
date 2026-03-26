from __future__ import annotations

from pathlib import Path

import discord
from discord.ext import commands

from ats_bot.bots.common import format_analysis_text
from ats_bot.config import settings
from ats_bot.core.ats_engine import analyze_resume_against_jd
from ats_bot.core.ai_mode import enhance_analysis_if_available, get_ai_mode_label
from ats_bot.core.parsers import parse_text_from_bytes
from ats_bot.core.resume_rewriter import rewrite_resume
from ats_bot.core.templates import TEMPLATE_STYLES, export_resume_file


def run_discord_bot() -> None:
    if not settings.discord_bot_token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN in environment.")

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        print(f"Discord bot logged in as {bot.user}")

    @bot.event
    async def on_command_error(ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        await ctx.send(f"Command error: {error}")

    @bot.command(name="help_ats")
    async def help_ats(ctx: commands.Context) -> None:
        await ctx.send(
            "Use: `!ats [classic|modern|minimal]` and attach exactly 2 files in same message:\n"
            "1) JD (.txt/.pdf/.doc/.docx)\n"
            "2) Resume (.txt/.pdf/.doc/.docx)"
        )

    @bot.command(name="ats")
    async def ats(ctx: commands.Context, template: str = "classic") -> None:
        template = template.lower()
        if template not in TEMPLATE_STYLES:
            await ctx.send("Template must be one of: classic, modern, minimal.")
            return

        attachments = ctx.message.attachments
        if len(attachments) < 2:
            await ctx.send("Attach JD and resume files in the same message.")
            return

        jd_file, resume_file = attachments[0], attachments[1]
        try:
            jd_text = parse_text_from_bytes(jd_file.filename, await jd_file.read())
            resume_text = parse_text_from_bytes(resume_file.filename, await resume_file.read())
        except Exception as exc:
            await ctx.send(f"Failed to parse files: {exc}")
            return

        base_analysis = analyze_resume_against_jd(jd_text, resume_text)
        analysis = enhance_analysis_if_available(jd_text, resume_text, base_analysis)
        ai_applied = (
            analysis.strengths != base_analysis.strengths
            or analysis.improvements != base_analysis.improvements
            or analysis.missing_keywords != base_analysis.missing_keywords
        )
        improved = rewrite_resume(resume_text, jd_text, analysis=analysis)
        output_format = "pdf" if Path(resume_file.filename).suffix.lower() == ".pdf" else "docx"

        output_file = export_resume_file(
            resume_text=improved,
            style=template,
            output_format=output_format,
            output_dir=settings.output_dir,
            base_filename=f"discord_{ctx.author.id}",
        )

        try:
            await ctx.send(
                format_analysis_text(
                    analysis=analysis,
                    mode_label=get_ai_mode_label(),
                    ai_applied=ai_applied,
                )[:1900]
            )
            await ctx.send(
                f"Template selected: {template.title()} | Fixed resume:",
                file=discord.File(str(output_file)),
            )
        finally:
            output_file.unlink(missing_ok=True)

    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    run_discord_bot()
