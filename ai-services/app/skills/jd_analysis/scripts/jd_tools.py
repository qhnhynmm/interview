import re
from typing import Literal

from app.schemas.plan import Domain, RequirementsResult, SeniorityLevel

# ── Skill taxonomy (5 domains) with aliases ──────────────────────────────────

DOMAIN_SKILLS: dict[Domain, dict[str, list[str]]] = {
    "backend": {
        "python": ["python", "py"],
        "java": ["java"],
        "go": ["golang"],
        "fastapi": ["fastapi"],
        "django": ["django"],
        "spring": ["spring", "spring boot", "springboot"],
        "postgresql": ["postgresql", "postgres", "psql"],
        "mysql": ["mysql"],
        "redis": ["redis"],
        "kafka": ["kafka", "apache kafka"],
        "rest": ["rest", "restful", "rest api"],
        "graphql": ["graphql"],
        "microservices": ["microservices", "microservice"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
    },
    "frontend": {
        "javascript": ["javascript", "js"],
        "typescript": ["typescript", "ts"],
        "react": ["react", "reactjs", "react.js"],
        "vue": ["vue", "vuejs", "vue.js"],
        "angular": ["angular"],
        "nextjs": ["next.js", "nextjs", "next js"],
        "html": ["html", "html5"],
        "css": ["css", "css3"],
        "webpack": ["webpack"],
        "vite": ["vite"],
        "testing": ["jest", "vitest", "cypress", "playwright"],
    },
    "data": {
        "python": ["python", "py"],
        "sql": ["sql"],
        "spark": ["spark", "apache spark", "pyspark"],
        "pandas": ["pandas"],
        "airflow": ["airflow", "apache airflow"],
        "dbt": ["dbt"],
        "etl": ["etl"],
        "snowflake": ["snowflake"],
        "bigquery": ["bigquery", "big query"],
        "machine learning": ["machine learning", "ml"],
        "tensorflow": ["tensorflow"],
        "pytorch": ["pytorch"],
    },
    "devops": {
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "terraform": ["terraform"],
        "ansible": ["ansible"],
        "aws": ["aws", "amazon web services"],
        "gcp": ["gcp", "google cloud"],
        "azure": ["azure"],
        "ci/cd": ["ci/cd", "cicd", "ci cd", "continuous integration"],
        "linux": ["linux"],
        "monitoring": ["prometheus", "grafana", "datadog"],
        "nginx": ["nginx"],
    },
    "ai": {
        "python": ["python", "py"],
        "machine learning": ["machine learning", "ml"],
        "deep learning": ["deep learning", "dl"],
        "llm": ["llm", "large language model", "language model"],
        "pytorch": ["pytorch"],
        "tensorflow": ["tensorflow"],
        "nlp": ["nlp", "natural language processing"],
        "rag": ["rag", "retrieval augmented"],
        "transformers": ["transformers", "huggingface"],
        "openai": ["openai"],
        "langchain": ["langchain"],
        "vector database": ["vector database", "vector db", "pinecone", "weaviate"],
    },
}

DOMAIN_KEYWORDS: dict[Domain, list[str]] = {
    "backend": ["backend", "back-end", "api engineer", "server", "microservice"],
    "frontend": ["frontend", "front-end", "ui engineer", "web developer", "react developer"],
    "data": ["data engineer", "data scientist", "analytics", "etl", "warehouse", "bi "],
    "devops": ["devops", "sre", "site reliability", "platform engineer", "infrastructure"],
    "ai": ["ai engineer", "ml engineer", "machine learning", "llm", "nlp", "deep learning"],
}

SENIORITY_PATTERNS: list[tuple[SeniorityLevel, list[str], int]] = [
    ("manager", ["engineering manager", "head of", "director", " vp ", "vice president"], 4),
    ("senior", ["senior", "sr.", "sr ", "lead", "principal", "staff", "architect"], 3),
    ("mid", ["mid-level", "mid level", "intermediate", " ii ", "2-5 years", "3+ years", "3-5"], 2),
    ("junior", ["junior", "jr.", "jr ", "entry level", "entry-level", "graduate", "intern", "0-2 years", "1-2 years"], 1),
]

_NICE_MARKERS = re.compile(
    r"(?:nice to have|preferred|plus|bonus|desirable|optional)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)",
    re.IGNORECASE | re.DOTALL,
)
_YEARS_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)


def _word_boundary_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


def _find_skills_in_text(text: str, domain: Domain) -> tuple[list[str], list[str]]:
    """Return (required_hits, nice_hits) canonical skill names."""
    required: list[str] = []
    nice: list[str] = []
    lower = text.lower()

    nice_section = ""
    for match in _NICE_MARKERS.finditer(text):
        nice_section += " " + match.group(1)

    taxonomy = DOMAIN_SKILLS[domain]
    for all_domains in DOMAIN_SKILLS.values():
        for canonical, aliases in all_domains.items():
            if canonical in required:
                continue
            for alias in aliases:
                if _word_boundary_pattern(alias).search(lower):
                    required.append(canonical)
                    break

    if nice_section:
        for all_domains in DOMAIN_SKILLS.values():
            for canonical, aliases in all_domains.items():
                if canonical in nice:
                    continue
                for alias in aliases:
                    if _word_boundary_pattern(alias).search(nice_section.lower()):
                        nice.append(canonical)
                        break

    def _unique(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    req_unique = _unique(required)
    nice_unique = [s for s in _unique(nice) if s not in req_unique]
    return req_unique, nice_unique


def _detect_domain(jd_text: str, position: str | None) -> Domain:
    combined = f"{position or ''} {jd_text}".lower()
    scores: dict[Domain, int] = {d: 0 for d in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if _word_boundary_pattern(kw).search(combined):
                scores[domain] += 2
    for domain, taxonomy in DOMAIN_SKILLS.items():
        for aliases in taxonomy.values():
            for alias in aliases:
                if _word_boundary_pattern(alias).search(combined):
                    scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    if scores[best] == 0:
        return "backend"
    return best


def _detect_seniority(jd_text: str, position: str | None) -> tuple[SeniorityLevel, int | None]:
    combined = f"{position or ''} {jd_text}".lower()
    best_level: SeniorityLevel = "mid"
    best_score = 0

    for level, patterns, weight in SENIORITY_PATTERNS:
        for pat in patterns:
            if _word_boundary_pattern(pat).search(combined):
                if weight > best_score:
                    best_score = weight
                    best_level = level

    min_years: int | None = None
    years_found = [int(m.group(1)) for m in _YEARS_RE.finditer(combined)]
    if years_found:
        min_years = min(years_found)
        if min_years <= 2:
            if best_score < 3:
                best_level = "junior"
        elif min_years >= 7 and best_score < 4:
            best_level = "senior"
        elif min_years >= 5 and best_level == "junior":
            best_level = "mid"

    return best_level, min_years


def extract_requirements(jd_text: str, position: str | None = None) -> RequirementsResult:
    domain = _detect_domain(jd_text, position)
    seniority_level, min_years = _detect_seniority(jd_text, position)
    required, nice = _find_skills_in_text(jd_text, domain)

    # Cross-domain skills mentioned in JD
    if not required:
        for dom in DOMAIN_SKILLS:
            if dom == domain:
                continue
            extra, _ = _find_skills_in_text(jd_text, dom)  # noqa: SLF001
            for skill in extra:
                if skill not in required:
                    required.append(skill)

    return RequirementsResult(
        required_skills=required[:12],
        seniority_level=seniority_level,
        domain=domain,
        min_years_experience=min_years,
        nice_to_have=nice[:8],
    )


def has_tech_skills(required_skills: list[str]) -> bool:
    return len(required_skills) > 0