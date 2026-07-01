from __future__ import annotations

from app.agents.inspector.plan_adapter import PlanContext
from app.schemas.inspector.evaluation import EvaluationRequest
from app.schemas.inspector.scorecard import (
    CodingEval,
    CompetencyScore,
    IntegritySummary,
    Recommendation,
    ScoreCard,
)


def _rec_from_score(score: float, integrity: IntegritySummary) -> Recommendation:
    if integrity.risk == "high" and score < 3.5:
        return Recommendation.strong_no_hire
    if score >= 4.5:
        return Recommendation.strong_hire
    if score >= 4.0:
        return Recommendation.hire
    if score >= 3.2:
        return Recommendation.lean_hire
    if score >= 2.5:
        return Recommendation.no_hire
    return Recommendation.strong_no_hire


def build_fallback_scorecard(
    req: EvaluationRequest,
    plan_ctx: PlanContext,
    integrity: IntegritySummary,
) -> ScoreCard:
    turns = len(req.transcript or [])
    base = 3.5 if turns >= 4 else 3.0 if turns >= 1 else 2.5
    if integrity.risk == "high":
        base = min(base, 2.5)
    elif integrity.risk == "medium":
        base = min(base, 3.2)

    competencies: list[CompetencyScore] = []
    for c in plan_ctx.competencies:
        competencies.append(
            CompetencyScore(
                name=c["name"],
                score=round(base, 1),
                weight=c["weight"],
                rationale=(
                    f"Provisional score based on {turns} transcript turn(s)."
                    if req.language != "vi"
                    else f"Điểm tạm dựa trên {turns} lượt hội thoại."
                ),
                evidence=None,
            )
        )

    overall = round(
        sum(x.score * x.weight for x in competencies) / (sum(x.weight for x in competencies) or 1),
        2,
    )
    rec = _rec_from_score(overall, integrity)

    coding_eval = None
    if plan_ctx.track == "tech":
        run = req.last_run_result or req.assignment_result or {}
        tp = run.get("tests_passed")
        tt = run.get("tests_total")
        correctness = 3.0
        if tp is not None and tt:
            correctness = round(float(tp) / float(tt) * 5, 1)
        coding_eval = CodingEval(
            correctness=correctness,
            code_quality=3.0,
            problem_solving=overall,
            communication=overall,
            tests_passed=tp,
            tests_total=tt,
            notes="",
        )

    if req.language == "vi":
        headline = f"Đánh giá tổng thể {overall}/5 cho {req.candidate_name}."
        summary = (
            f"Buổi phỏng vấn ghi nhận {turns} lượt hội thoại. "
            f"Toàn vẹn proctoring: {integrity.note}"
        )
        strengths = ["Tham gia đầy đủ buổi phỏng vấn"] if turns else []
        concerns = ["LLM scoring unavailable — điểm tạm thời"] if turns else ["Thiếu transcript"]
    else:
        headline = f"Overall evaluation {overall}/5 for {req.candidate_name}."
        summary = (
            f"Interview captured {turns} transcript turn(s). "
            f"Proctoring integrity: {integrity.note}"
        )
        strengths = ["Completed interview session"] if turns else []
        concerns = ["LLM scoring unavailable — provisional scores"] if turns else ["No transcript recorded"]

    return ScoreCard(
        candidate_name=req.candidate_name,
        position=req.position,
        track=plan_ctx.track,  # type: ignore[arg-type]
        overall_score=overall,
        recommendation=rec,
        headline=headline,
        summary=summary,
        competencies=competencies,
        strengths=strengths,
        concerns=concerns,
        red_flags=["High proctoring risk"] if integrity.risk == "high" else [],
        coding_eval=coding_eval,
        next_steps="Schedule follow-up with hiring manager." if req.language != "vi" else "Lên lịch vòng tiếp theo với hiring manager.",
    )