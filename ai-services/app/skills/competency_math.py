from app.schemas.api.common import CompetencyItem, TopicItem
from app.schemas.internal.planning import AnalystGrounding

_DEFAULT_COMPETENCIES: list[tuple[str, float]] = [
    ("Technical depth", 0.30),
    ("Problem solving", 0.25),
    ("Communication", 0.25),
    ("Culture fit", 0.20),
]

_DEFAULT_TOPICS: list[tuple[str, float, int]] = [
    ("Introduction & background", 0.15, 3),
    ("Technical depth", 0.35, 6),
    ("Coding exercise", 0.35, 5),
    ("Wrap-up", 0.15, 1),
]


def _normalize_weights(items: list[tuple[str, float]]) -> list[CompetencyItem]:
    total = sum(w for _, w in items) or 1.0
    return [CompetencyItem(name=name, weight=round(w / total, 2)) for name, w in items]


def build_competencies(grounding: AnalystGrounding) -> list[CompetencyItem]:
    if len(grounding.skill_evidence) >= 4:
        boosted = list(_DEFAULT_COMPETENCIES)
        boosted[0] = ("Technical depth", 0.35)
        boosted[1] = ("Problem solving", 0.30)
        boosted[2] = ("Communication", 0.20)
        boosted[3] = ("Culture fit", 0.15)
        return _normalize_weights(boosted)
    return _normalize_weights(list(_DEFAULT_COMPETENCIES))


def build_topics(*, has_coding: bool = True) -> list[TopicItem]:
    rows = list(_DEFAULT_TOPICS)
    if not has_coding:
        rows = [r for r in rows if "coding" not in r[0].lower()]
        rows.append(("Scenario discussion", 0.35, 5))
    total = sum(w for _, w, _ in rows) or 1.0
    return [TopicItem(topic=t, weight=round(w / total, 2), minutes=m) for t, w, m in rows]