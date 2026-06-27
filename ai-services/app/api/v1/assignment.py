from fastapi import APIRouter

from app.agents.assignment.agent import AssignmentAgent
from app.schemas.api.assignment import AssignmentGenerateRequest, AssignmentGenerateResponse

router = APIRouter(prefix="/assignment", tags=["assignment"])
_agent = AssignmentAgent()


@router.post("/generate", response_model=AssignmentGenerateResponse)
async def generate_assignment(body: AssignmentGenerateRequest) -> AssignmentGenerateResponse:
    assignment, meta = await _agent.run(body)
    return AssignmentGenerateResponse(assignment=assignment, meta=meta)