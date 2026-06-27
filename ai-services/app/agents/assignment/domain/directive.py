import re
from dataclasses import dataclass

from app.schemas.plan import AssignmentDirective, AssignmentMode, AssignmentType, Difficulty
from app.skills.jd_analysis.scripts.jd_tools import extract_requirements, has_tech_skills
from app.skills.interview_planning.scripts.planning_tools import build_assignment_directive

_DIRECTIVE_RE = re.compile(
    r"ASSIGNMENT\s+DIRECTIVE\s*→\s*type:\s*(\w+)\s*·\s*mode:\s*(\w+)\s*·\s*"
    r"ai_assistant:\s*(\w+)\s*·\s*difficulty:\s*(\w+)",
    re.IGNORECASE,
)

_NONTECH_KEYWORDS = re.compile(
    r"\b(marketing|sales|hr\b|human resources|recruiter|account manager|business development)\b",
    re.IGNORECASE,
)


@dataclass
class ResolvedTrack:
    track: str  # tech | nontech
    domain: str
    level: str


def parse_assignment_directive(brief: str) -> AssignmentDirective | None:
    if not brief.strip():
        return None
    first_line = brief.strip().splitlines()[0]
    match = _DIRECTIVE_RE.search(first_line)
    if not match:
        return None
    raw_type, raw_mode, raw_ai, raw_diff = match.groups()
    try:
        a_type: AssignmentType = raw_type.lower()  # type: ignore[assignment]
        if a_type not in ("coding", "cognitive"):
            return None
        mode: AssignmentMode = "dsa"  # type: ignore[assignment]
        if a_type == "coding":
            mode = raw_mode.lower()  # type: ignore[assignment]
            if mode not in ("dsa", "project"):
                mode = "dsa"
        ai = raw_ai.lower() in ("enabled", "true", "yes", "on")
        diff: Difficulty = raw_diff.lower()  # type: ignore[assignment]
        if diff not in ("easy", "medium", "hard"):
            diff = "medium"
        return AssignmentDirective(type=a_type, mode=mode, ai_assistant=ai, difficulty=diff)
    except Exception:
        return None


def infer_track(position: str | None, jd_text: str) -> str:
    combined = f"{position or ''} {jd_text}"
    if _NONTECH_KEYWORDS.search(combined):
        return "nontech"
    req = extract_requirements(jd_text, position)
    return "tech" if has_tech_skills(req.required_skills) or req.domain != "backend" else "tech"


def infer_domain_and_level(
    *,
    position: str | None,
    jd_text: str,
    cv_markdown: str,
    level: str | None,
) -> ResolvedTrack:
    req = extract_requirements(jd_text, position)
    track = infer_track(position, jd_text)
    resolved_level = (level or req.seniority_level).lower()
    if resolved_level not in ("junior", "mid", "senior", "manager"):
        resolved_level = req.seniority_level
    if resolved_level == "manager":
        resolved_level = "senior"
    return ResolvedTrack(track=track, domain=req.domain, level=resolved_level)


def default_directive(
    *,
    position: str | None,
    jd_text: str,
    level: str | None,
) -> AssignmentDirective:
    req = extract_requirements(jd_text, position)
    lvl = level or req.seniority_level
    if lvl == "manager":
        lvl = "senior"
    return build_assignment_directive(required_skills=req.required_skills, seniority_level=lvl)  # type: ignore[arg-type]