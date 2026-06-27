from fastapi import APIRouter

from app.agents.inspector.agent import InspectorAgent
from app.schemas.api.inspector import InspectorEvaluateRequest, InspectorEvaluateResponse

router = APIRouter(prefix="/inspector", tags=["inspector"])
_agent = InspectorAgent()


@router.post("/evaluate", response_model=InspectorEvaluateResponse)
async def evaluate(body: InspectorEvaluateRequest) -> InspectorEvaluateResponse:
    report, meta = await _agent.run(body)
    return InspectorEvaluateResponse(report=report, meta=meta)