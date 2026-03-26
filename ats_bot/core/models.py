from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ATSAnalysis:
    score: float
    keyword_coverage: float
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "keyword_coverage": self.keyword_coverage,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }


@dataclass
class ResumeData:
    name: str
    email: str | None
    phone: str | None
    links: list[str]
    sections: dict[str, list[str]]

