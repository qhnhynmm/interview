from fastapi import APIRouter

from app.agents.inspector.agent import InspectorAgent
from app.infra.tracing import set_span_attributes, trace_span
from app.schemas.api.inspector import InspectorEvaluateRequest, InspectorEvaluateResponse

router = APIRouter(prefix="/inspector", tags=["inspector"])
_agent = InspectorAgent()


@router.post("/evaluate", response_model=InspectorEvaluateResponse)
async def evaluate(body: InspectorEvaluateRequest) -> InspectorEvaluateResponse:
    with trace_span(
        "api.inspector.evaluate",
        kind="AGENT",
        agent="inspector",
        interview_id=body.interview_id,
    ):
        report, meta = await _agent.run(body)
        set_span_attributes(
            overall_score=report.get("overall_score"),
            transcript_turns=report.get("transcript_turns"),
            llm_used=meta.get("llm_used"),
            track=meta.get("track"),
        )
        return InspectorEvaluateResponse(
            interview_id=body.interview_id,
            report=report,
            report_markdown=meta.get("report_markdown", ""),
            pdf_base64=meta.get("pdf_base64", ""),
            source="inspector-agent",
            meta=meta,
        )