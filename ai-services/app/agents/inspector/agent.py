from __future__ import annotations

import logging
from typing import Any

from app.agents.inspector.fallback import build_fallback_scorecard
from app.agents.inspector.integrity import compute_integrity, summarize_integrity
from app.agents.inspector.llm_scorer import score_with_llm
from app.agents.inspector.plan_adapter import extract_plan_context
from app.agents.inspector.report_builder import scorecard_to_report
from app.agents.inspector.scoring import apply_integrity_and_gates
from app.agents.base import AgentBase
from app.config import get_settings
from app.schemas.inspector.evaluation import EvaluationRequest
from app.schemas.inspector.scorecard import IntegritySummary, ScoreCard

logger = logging.getLogger(__name__)


class InspectorAgent(AgentBase):
    name = "inspector"

    async def run(self, request: EvaluationRequest) -> tuple[dict[str, Any], dict[str, Any]]:
        settings = get_settings()
        plan_ctx = extract_plan_context(
            request.plan,
            request.assignment,
            track_override=request.track,
        )
        if not request.evaluation_brief:
            request = request.model_copy(update={"evaluation_brief": plan_ctx.evaluation_brief})
        if not request.interview_brief:
            request = request.model_copy(update={"interview_brief": plan_ctx.interview_brief})
        if not request.candidate_name:
            request = request.model_copy(update={"candidate_name": "Candidate"})
        if not request.position:
            request = request.model_copy(update={"position": "Role"})

        integrity = summarize_integrity(request.proctor_events, language=request.language)
        legacy_integrity = compute_integrity(request.proctor_events)
        integrity_dict = {**integrity.model_dump(), **legacy_integrity}

        scoring_source = "fallback"
        scorecard: ScoreCard | None = None

        if settings.llm_enabled:
            scorecard = await score_with_llm(request, plan_ctx, integrity_dict, settings)
            if scorecard is not None:
                scoring_source = "llm"
                scorecard = self._backfill_scorecard(scorecard, request, plan_ctx)

        if scorecard is None:
            scorecard = build_fallback_scorecard(request, plan_ctx, integrity)

        eval_brief = request.evaluation_brief or plan_ctx.evaluation_brief
        scorecard = apply_integrity_and_gates(
            scorecard,
            plan_ctx=plan_ctx,
            integrity=integrity,
            evaluation_brief=eval_brief,
        )

        llm_used = scoring_source == "llm"
        report, markdown, pdf_b64 = scorecard_to_report(
            scorecard,
            integrity,
            interview_id=request.interview_id,
            language=request.language,
            scoring_source=scoring_source,
            pdf_base64="",
            report_markdown="",
        )
        report["transcript_turns"] = len(request.transcript or [])
        report["proctoring_events"] = len(request.proctor_events or [])

        meta = {
            "agent": self.name,
            "llm_used": llm_used,
            "scoring_source": scoring_source,
            "track": plan_ctx.track,
            "report_markdown": markdown,
            "pdf_base64": pdf_b64,
        }
        return report, meta

    def _backfill_scorecard(
        self,
        card: ScoreCard,
        req: EvaluationRequest,
        plan_ctx: Any,
    ) -> ScoreCard:
        run = req.last_run_result or req.assignment_result or {}
        updates: dict[str, Any] = {
            "candidate_name": req.candidate_name,
            "position": req.position,
            "track": plan_ctx.track,
        }
        if plan_ctx.track == "tech":
            coding_eval = card.coding_eval
            if coding_eval is None:
                from app.agents.inspector.llm_scorer import _parse_coding_eval

                coding_eval = _parse_coding_eval(None, req)
            if coding_eval and run:
                coding_eval = coding_eval.model_copy(
                    update={
                        "tests_passed": run.get("tests_passed", coding_eval.tests_passed),
                        "tests_total": run.get("tests_total", coding_eval.tests_total),
                    }
                )
                updates["coding_eval"] = coding_eval
        return card.model_copy(update=updates)

    async def run_legacy(self, body: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Accept legacy InspectorEvaluateRequest dict."""
        return await self.run(EvaluationRequest.from_legacy(body))