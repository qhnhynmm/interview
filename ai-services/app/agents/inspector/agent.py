from app.agents.base import AgentBase
from app.agents.inspector.integrity import compute_integrity
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

        integrity = compute_integrity(request.proctoring_events)
        overall = round(sum(scores.values()) / len(scores), 2)
        if integrity["integrity_flag"]:
            overall = round(min(overall, 2.5), 2)

        summary_parts = [
            f"Integrity score {integrity['integrity_score']}/100 ({integrity['integrity_band']}).",
        ]
        if integrity["incident_count"]:
            summary_parts.append(
                f"{integrity['incident_count']} proctoring incident(s) recorded.",
            )
        else:
            summary_parts.append("No proctoring incidents recorded.")

        report = {
            "interview_id": request.interview_id,
            "is_mock": not self.llm.enabled,
            "overall_score": overall,
            "competency_scores": scores,
            "transcript_turns": len(request.transcript),
            "proctoring_events": len(request.proctoring_events),
            "integrity": integrity,
            "summary": " ".join(summary_parts),
        }
        meta = {"agent": self.name, "llm_used": False}
        return report, meta