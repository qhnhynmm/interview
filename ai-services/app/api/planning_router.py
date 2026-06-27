from fastapi import APIRouter

from app.agents.planning.agent import run_planning_agent
from app.schemas.plan import PlanRequest, PlanResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/plan", response_model=PlanResponse)
async def create_plan(body: PlanRequest) -> PlanResponse:
    """Planning Agent — sinh 3 golden brief markdown cho downstream agents."""
    plan, meta = await run_planning_agent(body)
    return PlanResponse(plan=plan, meta=meta)