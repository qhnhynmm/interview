from app.agents.base import AgentBase
from app.schemas.api.inspector import InspectorEvaluateRequest


class InspectorAgent(AgentBase):
    name = "inspector"

    async def run(self, request: InspectorEvaluateRequest) -> tuple[dict, dict]:
        competencies = request.plan.get("competencies") or []
        scores = {
            str(c.get("name", f"competency_{i}")): 3.5
            for i, c in enumerate(competencies)
            if isinstance(c, dict)
        } or {
            "Technical depth": 3.5,
            "Problem solving": 3.0,
            "Communication": 3.5,
            "Culture fit": 3.0,
        }

        report = {
            "interview_id": request.interview_id,
            "is_mock": not self.llm.enabled,
            "overall_score": round(sum(scores.values()) / len(scores), 2),
            "competency_scores": scores,
            "transcript_turns": len(request.transcript),
            "proctoring_events": len(request.proctoring_events),
            "summary": "Automated scaffold report — replace with Inspector LLM + PDF pipeline.",
        }
        meta = {"agent": self.name, "llm_used": False}
        return report, meta