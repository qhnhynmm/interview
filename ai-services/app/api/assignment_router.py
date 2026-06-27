from fastapi import APIRouter, HTTPException

from app.agents.assignment.agent import run_assignment_agent
from app.infra.tracing import set_span_attributes, trace_span
from app.schemas.assignment import AssignmentRequest, AssignmentResponse

router = APIRouter(prefix="/assignment", tags=["assignment"])


@router.post("/generate", response_model=AssignmentResponse)
async def generate_assignment(body: AssignmentRequest) -> AssignmentResponse:
    with trace_span(
        "api.assignment.generate",
        kind="AGENT",
        agent="assignment",
        interview_id=body.interview_id,
    ):
        try:
            assignment, meta = await run_assignment_agent(body)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        set_span_attributes(
            assignment_type=assignment.type.value,
            source=assignment.source,
            llm_used=meta.get("llm_used"),
            path=meta.get("path"),
        )
        return AssignmentResponse(assignment=assignment, meta=meta)