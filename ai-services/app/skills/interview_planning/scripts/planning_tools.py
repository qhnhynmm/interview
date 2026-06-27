import re
from typing import Literal

from app.schemas.plan import (
    AssignmentDirective,
    AssignmentMode,
    AssignmentType,
    Competency,
    Difficulty,
    Domain,
    ProblemBankEntry,
    RequirementsResult,
    SeniorityLevel,
    SkillMatchResult,
)
from app.skills.interview_planning.scripts.problem_bank import PROBLEM_BANK, _LEVEL_ALIASES
from app.skills.jd_analysis.scripts.jd_tools import DOMAIN_SKILLS, _word_boundary_pattern, has_tech_skills

_CANONICAL_ALIASES: dict[str, list[str]] = {}
for _taxonomy in DOMAIN_SKILLS.values():
    for canonical, aliases in _taxonomy.items():
        _CANONICAL_ALIASES.setdefault(canonical, [])
        for alias in aliases:
            if alias not in _CANONICAL_ALIASES[canonical]:
                _CANONICAL_ALIASES[canonical].append(alias)


def _normalize_level(level: SeniorityLevel) -> str:
    return _LEVEL_ALIASES.get(level, "mid")


def _skill_in_text(text: str, canonical: str) -> bool:
    aliases = _CANONICAL_ALIASES.get(canonical, [canonical])
    for alias in aliases:
        if _word_boundary_pattern(alias).search(text):
            return True
    return _word_boundary_pattern(canonical).search(text) is not None


def match_skills(cv_markdown: str, required_skills: list[str]) -> SkillMatchResult:
    text = cv_markdown.lower()
    matched: list[str] = []
    gaps: list[str] = []
    for skill in required_skills:
        if _skill_in_text(text, skill):
            matched.append(skill)
        else:
            gaps.append(skill)

    score = len(matched) / len(required_skills) if required_skills else 0.0
    return SkillMatchResult(
        matched_skills=matched,
        skill_gaps=gaps,
        match_score=round(score, 3),
    )


def search_problem_bank(domain: Domain, level: SeniorityLevel) -> ProblemBankEntry | None:
    norm = _normalize_level(level)
    chain: list[tuple[Domain, str]] = [
        (domain, norm),
        (domain, "mid"),
        ("backend", norm),
        ("backend", "mid"),
    ]
    for key in chain:
        entries = PROBLEM_BANK.get(key)
        if entries:
            return entries[0]
    return None


def build_assignment_directive(
    *,
    required_skills: list[str],
    seniority_level: SeniorityLevel,
) -> AssignmentDirective:
    assignment_type: AssignmentType = "coding" if has_tech_skills(required_skills) else "cognitive"
    if seniority_level == "junior":
        return AssignmentDirective(
            type=assignment_type,
            mode="dsa",
            ai_assistant=False,
            difficulty="easy",
        )
    if seniority_level == "senior" or seniority_level == "manager":
        return AssignmentDirective(
            type=assignment_type,
            mode="project",
            ai_assistant=True,
            difficulty="hard",
        )
    return AssignmentDirective(
        type=assignment_type,
        mode="project",
        ai_assistant=True,
        difficulty="medium",
    )


def _title_case_skill(skill: str) -> str:
    return skill.replace("_", " ").title()


def build_competencies(
    *,
    requirements: RequirementsResult,
    match: SkillMatchResult,
) -> list[Competency]:
    raw_weights: list[tuple[str, float]] = []

    for skill in requirements.required_skills[:4]:
        multiplier = 2.0
        name = f"{_title_case_skill(skill)} depth"
        raw_weights.append((name, multiplier))

    for gap in match.skill_gaps[:3]:
        name = f"{_title_case_skill(gap)} (gap probe)"
        raw_weights.append((name, 1.5))

    if match.matched_skills:
        raw_weights.append(("Evidence-backed experience", 1.8))

    raw_weights.append(("Communication & clarity", 1.2))
    raw_weights.append(("Ownership & trade-offs", 1.0))

    # Deduplicate by name (keep max weight)
    merged: dict[str, float] = {}
    for name, w in raw_weights:
        merged[name] = max(merged.get(name, 0), w)

    items = list(merged.items())[:6]
    if len(items) < 3:
        items.extend(
            [
                ("Problem solving", 1.5),
                ("System thinking", 1.3),
            ]
        )
    items = items[:6]

    return renormalize_competencies(items)


def renormalize_competencies(raw: list[tuple[str, float]] | list[Competency]) -> list[Competency]:
    if not raw:
        return [
            Competency(name="Technical depth", weight=35),
            Competency(name="Problem solving", weight=35),
            Competency(name="Communication", weight=30),
        ]

    if isinstance(raw[0], Competency):
        pairs = [(c.name, float(c.weight)) for c in raw]  # type: ignore[union-attr]
    else:
        pairs = raw  # type: ignore[assignment]

    total = sum(w for _, w in pairs) or 1.0
    scaled = [Competency(name=name, weight=max(1, round(w / total * 100))) for name, w in pairs]

    drift = sum(c.weight for c in scaled) - 100
    if drift != 0 and scaled:
        scaled[-1] = Competency(name=scaled[-1].name, weight=scaled[-1].weight - drift)

    return scaled


def duration_for_seniority(level: SeniorityLevel) -> int:
    return {"junior": 45, "mid": 50, "senior": 60, "manager": 60}[level]


def extract_evidence_quotes(cv_markdown: str, skills: list[str], limit: int = 5) -> list[tuple[str, str]]:
    lines = [ln.strip() for ln in cv_markdown.splitlines() if ln.strip()]
    quotes: list[tuple[str, str]] = []
    for skill in skills:
        for line in lines:
            if _skill_in_text(line, skill):
                quotes.append((skill, line[:160]))
                break
        if len(quotes) >= limit:
            break
    return quotes