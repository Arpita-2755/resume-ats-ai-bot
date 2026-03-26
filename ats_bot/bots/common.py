from __future__ import annotations

from ats_bot.core.models import ATSAnalysis


def format_analysis_text(analysis: ATSAnalysis) -> str:
    lines = [
        f"ATS Score: {analysis.score}/10",
        f"Keyword Coverage: {int(analysis.keyword_coverage * 100)}%",
    ]
    if analysis.breakdown:
        lines.append(
            "Breakdown: "
            + ", ".join(
                [f"{key.replace('_', ' ').title()}={value}" for key, value in analysis.breakdown.items()]
            )
        )
    lines.extend(
        [
            "",
            "Strengths:",
        ]
    )
    lines.extend([f"- {item}" for item in analysis.strengths[:4]])
    lines.append("")
    lines.append("Improvements:")
    lines.extend([f"- {item}" for item in analysis.improvements[:5]])
    if analysis.missing_keywords:
        lines.append("")
        lines.append("Missing Keywords (Top): " + ", ".join(analysis.missing_keywords[:8]))
    return "\n".join(lines)
