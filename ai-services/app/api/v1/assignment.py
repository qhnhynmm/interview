from fastapi import APIRouter

from app.agents.assignment.agent import AssignmentAgent
from app.infra.tracing import set_span_attributes, trace_span
from app.schemas.api.assignment import AssignmentGenerateRequest, AssignmentGenerateResponse

router = APIRouter(prefix="/assignment", tags=["assignment"])
_agent = AssignmentAgent()


@router.post("/generate", response_model=AssignmentGenerateResponse)
async def generate_assignment(body: AssignmentGenerateRequest) -> AssignmentGenerateResponse:
    with trace_span("api.assignment.generate", kind="AGENT", agent="assignment", mode=body.mode):
        assignment, meta = await _agent.run(body)
        set_span_attributes(title=assignment.title, llm_used=meta.get("llm_used"))
        return AssignmentGenerateResponse(assignment=assignment, meta=meta)