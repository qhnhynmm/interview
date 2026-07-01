"""Direct JSON LLM scoring — avoids Gemini MAF tool-calling (thought_signature)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.agents.inspector.plan_adapter import PlanContext
from app.agents.inspector.tools import _search_transcript_impl, _weighted_overall
from app.config import Settings
from app.schemas.inspector.evaluation import EvaluationRequest
from app.schemas.inspector.scorecard import (
    CodingEval,
    CompetencyScore,
    Recommendation,
    ScoreCard,
)

logger = logging.getLogger(__name__)

_REC_VALUES = {r.value for r in Recommendation}


def _system_prompt(language: str) -> str:
    lang = "Vietnamese" if language.lower().startswith("vi") else "English"
    return f"""You are the Inspector hiring evaluator for technical interviews.

Return ONE minified JSON object (no markdown fences) with keys:
- competencies: array of {{name, score, rationale, evidence}} — one per rubric competency
- headline: string (one line, {lang})
- summary: string (2-4 sentences, {lang})
- recommendation: one of strong_hire|hire|lean_hire|no_hire|strong_no_hire
- strengths: string[]
- concerns: string[]
- red_flags: string[]
- coding_eval (tech track only): {{correctness, code_quality, problem_solving, communication, notes}} each 0-5
- next_steps: string

Scoring scale: 5=Exceptional, 4=Strong, 3=Adequate, 2=Below, 1=Weak, 0=No evidence.
- Score ONLY from transcript quotes and coding/test evidence provided.
- Never invent proctoring facts — integrity block is pre-computed.
- evidence must be a short quote or paraphrase from the transcript (or "no evidence").
- If transcript is empty, score 0-2 and note missing evidence in concerns.
- Apply the evaluation rubric HARD GATE and integrity caps mentally; post-processing will enforce caps.
Write headline, summary, rationales in {lang}."""


def _format_transcript(transcript: list[dict], *, limit: int = 40) -> str:
    lines: list[str] = []
    for turn in transcript[:limit]:
        role = turn.get("role", "?")
        content = str(turn.get("content") or "").strip()
        if content:
            lines.append(f"[{role}] {content[:500]}")
    return "\n".join(lines) or "(empty — no spoken turns recorded)"


def _coding_block(req: EvaluationRequest, plan_ctx: PlanContext) -> str:
    if plan_ctx.track != "tech":
        return "Track: non-technical (no coding eval required)."
    coding = (req.assignment or {}).get("coding") or {}
    run = req.last_run_result or req.assignment_result or {}
    parts = [
        f"Assignment: {coding.get('title') or 'n/a'}",
        f"Tests: {run.get('tests_passed', '?')}/{run.get('tests_total', '?')}",
        f"Code snippet:\n{(req.coding_submission or '')[:3000]}",
    ]
    if run.get("stderr"):
        parts.append(f"stderr: {str(run['stderr'])[:400]}")
    return "\n".join(parts)


def _build_user_message(
    req: EvaluationRequest,
    plan_ctx: PlanContext,
    integrity_dict: dict[str, Any],
) -> str:
    comp_lines = "\n".join(
        f"- {c['name']}: weight={c['weight']:.0%}" for c in plan_ctx.competencies
    )
    return f"""Evaluate interview {req.interview_id}.

Candidate: {req.candidate_name}
Position: {req.position}
Track: {plan_ctx.track}
Language: {req.language}

=== EVALUATION RUBRIC ===
{(req.evaluation_brief or plan_ctx.evaluation_brief or '(none)')[:3500]}

=== COMPETENCIES (score each) ===
{comp_lines}

=== INTERVIEW BRIEF (context) ===
{(req.interview_brief or plan_ctx.interview_brief or '')[:1500]}

=== TRANSCRIPT ({len(req.transcript or [])} turns) ===
{_format_transcript(list(req.transcript or []))}

=== CODING / ASSIGNMENT ===
{_coding_block(req, plan_ctx)}

=== INTEGRITY (pre-computed — do not override) ===
{json.dumps(integrity_dict, ensure_ascii=False)}
"""


def _parse_recommendation(raw: str) -> Recommendation:
    val = (raw or "").strip().lower()
    if val in _REC_VALUES:
        return Recommendation(val)
    return Recommendation.lean_hire


def _parse_competencies(
    rows: Any,
    plan_ctx: PlanContext,
) -> list[CompetencyScore]:
    weight_by_name = {c["name"].lower(): c["weight"] for c in plan_ctx.competencies}
    default_names = [c["name"] for c in plan_ctx.competencies]

    parsed: list[CompetencyScore] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()[:22]
            if not name:
                continue
            weight = weight_by_name.get(name.lower())
            if weight is None:
                for dn in default_names:
                    if dn.lower() in name.lower() or name.lower() in dn.lower():
                        weight = weight_by_name.get(dn.lower(), 0.25)
                        name = dn
                        break
            weight = weight if weight is not None else 0.25
            try:
                score = max(0.0, min(5.0, float(row.get("score", 0))))
            except (TypeError, ValueError):
                score = 0.0
            parsed.append(
                CompetencyScore(
                    name=name,
                    score=round(score, 1),
                    weight=weight,
                    rationale=str(row.get("rationale") or "")[:500],
                    evidence=str(row.get("evidence") or "")[:300] or None,
                )
            )

    seen = {c.name.lower() for c in parsed}
    for c in plan_ctx.competencies:
        if c["name"].lower() not in seen:
            parsed.append(
                CompetencyScore(
                    name=c["name"],
                    score=0.0,
                    weight=c["weight"],
                    rationale="Not scored by model.",
                    evidence=None,
                )
            )
    return parsed


def _parse_coding_eval(raw: Any, req: EvaluationRequest) -> CodingEval | None:
    if not isinstance(raw, dict):
        run = req.last_run_result or req.assignment_result or {}
        tp, tt = run.get("tests_passed"), run.get("tests_total")
        if tp is None and tt is None:
            return None
        correctness = 3.0
        if tp is not None and tt:
            correctness = round(float(tp) / float(tt) * 5, 1)
        return CodingEval(
            correctness=correctness,
            tests_passed=tp,
            tests_total=tt,
            notes=str(run.get("stderr") or "")[:300],
        )

    def _f(key: str, default: float = 3.0) -> float:
        try:
            return max(0.0, min(5.0, float(raw.get(key, default))))
        except (TypeError, ValueError):
            return default

    run = req.last_run_result or req.assignment_result or {}
    return CodingEval(
        correctness=_f("correctness"),
        code_quality=_f("code_quality"),
        problem_solving=_f("problem_solving"),
        communication=_f("communication"),
        tests_passed=run.get("tests_passed"),
        tests_total=run.get("tests_total"),
        notes=str(raw.get("notes") or run.get("stderr") or "")[:300],
    )


def parse_llm_scorecard(
    data: dict[str, Any],
    req: EvaluationRequest,
    plan_ctx: PlanContext,
) -> ScoreCard:
    competencies = _parse_competencies(data.get("competencies"), plan_ctx)
    overall = _weighted_overall(competencies)
    rec = _parse_recommendation(str(data.get("recommendation", "")))

    strengths = [str(s) for s in (data.get("strengths") or []) if str(s).strip()]
    concerns = [str(s) for s in (data.get("concerns") or []) if str(s).strip()]
    red_flags = [str(s) for s in (data.get("red_flags") or []) if str(s).strip()]

    coding_eval = None
    if plan_ctx.track == "tech":
        coding_eval = _parse_coding_eval(data.get("coding_eval"), req)

    return ScoreCard(
        candidate_name=req.candidate_name,
        position=req.position,
        track=plan_ctx.track,  # type: ignore[arg-type]
        overall_score=overall,
        recommendation=rec,
        headline=str(data.get("headline") or "")[:200],
        summary=str(data.get("summary") or "")[:2000],
        competencies=competencies,
        strengths=strengths[:8],
        concerns=concerns[:8],
        red_flags=red_flags[:8],
        coding_eval=coding_eval,
        next_steps=str(data.get("next_steps") or "")[:500] or None,
    )


async def score_with_llm(
    req: EvaluationRequest,
    plan_ctx: PlanContext,
    integrity_dict: dict[str, Any],
    settings: Settings,
) -> ScoreCard | None:
    if not settings.llm_enabled:
        return None

    body = {
        "model": settings.inspector_model_effective,
        "temperature": settings.inspector_temperature,
        "max_tokens": settings.inspector_max_tokens,
        "messages": [
            {"role": "system", "content": _system_prompt(req.language)},
            {"role": "user", "content": _build_user_message(req, plan_ctx, integrity_dict)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=settings.planning_request_timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            if not isinstance(data, dict):
                return None
            card = parse_llm_scorecard(data, req, plan_ctx)
            logger.info(
                "Inspector LLM scored %s — overall %.1f rec=%s comps=%d",
                req.interview_id,
                card.overall_score,
                card.recommendation.value,
                len(card.competencies),
            )
            return card
    except Exception as exc:
        logger.warning("Inspector LLM scoring failed for %s: %s", req.interview_id, exc)
        return None