import re

from app.schemas.internal.planning import AnalystGrounding, SkillEvidence

_SKILL_PATTERNS = (
    r"\b(python|java|javascript|typescript|react|node\.?js|sql|postgresql|docker|kubernetes|aws|gcp|azure|fastapi|django|spring|go|rust|c\+\+|machine learning|ml|ai|llm)\b"
)

_STOPWORDS = frozenset(
    "the a an and or for with from into about your our their this that will shall must have has".split()
)


def _tokenize_keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for word in words:
        if word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        result.append(word)
        if len(result) >= limit:
            break
    return result


def extract_cv_skills(cv_text: str) -> list[str]:
    if not cv_text.strip():
        return []
    found = {m.group(0).lower() for m in re.finditer(_SKILL_PATTERNS, cv_text, re.IGNORECASE)}
    return sorted(found)


def analyze_jd(
    *,
    jd_text: str,
    cv_text: str,
    position: str,
    seniority: str | None,
    language: str,
    candidate_name: str,
) -> AnalystGrounding:
    jd_keywords = _tokenize_keywords(jd_text)
    cv_skills = extract_cv_skills(cv_text)
    overlap = [s for s in cv_skills if any(s in k or k in s for k in jd_keywords)]

    evidence = [
        SkillEvidence(skill=skill, evidence=f"Mentioned in CV", confidence=0.7) for skill in cv_skills[:6]
    ]
    for skill in overlap[:4]:
        evidence.append(
            SkillEvidence(skill=skill, evidence="Matches JD keywords", confidence=0.85)
        )

    summary_parts = [f"Role: {position}"]
    if seniority:
        summary_parts.append(f"Level: {seniority}")
    if cv_skills:
        summary_parts.append(f"CV highlights: {', '.join(cv_skills[:5])}")
    if jd_keywords:
        summary_parts.append(f"JD focus: {', '.join(jd_keywords[:5])}")

    return AnalystGrounding(
        candidate_name=candidate_name,
        position=position,
        seniority=seniority,
        language=language,
        jd_keywords=jd_keywords,
        cv_skills=cv_skills,
        skill_evidence=evidence,
        summary="; ".join(summary_parts),
    )