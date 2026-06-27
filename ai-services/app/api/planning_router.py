from fastapi import APIRouter

from app.agents.planning.agent import run_planning_agent
from app.infra.tracing import set_span_attributes, trace_span
from app.schemas.plan import PlanRequest, PlanResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/plan", response_model=PlanResponse)
async def create_plan(body: PlanRequest) -> PlanResponse:
    """Planning Agent — sinh 3 golden brief markdown cho downstream agents."""
    with trace_span(
        "api.planning.plan",
        kind="CHAIN",
        position=body.position,
        candidate_name=body.candidate_name,
        language=body.language,
    ):
        plan, meta = await run_planning_agent(body)
        set_span_attributes(source=meta.get("source"), degraded_briefs=meta.get("degraded_briefs"))
        return PlanResponse(plan=plan, meta=meta)