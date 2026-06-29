import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.planning.agent import run_planning_agent
from app.infra.sse import sse_event
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


@router.post("/plan/stream")
async def create_plan_stream(body: PlanRequest) -> StreamingResponse:
    """Planning Agent with SSE progress events."""

    async def event_stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_progress(agent: str, text: str) -> None:
            await queue.put({"type": "progress", "agent": agent, "text": text})

        async def run() -> None:
            try:
                with trace_span(
                    "api.planning.plan.stream",
                    kind="CHAIN",
                    position=body.position,
                    candidate_name=body.candidate_name,
                ):
                    plan, meta = await run_planning_agent(body, progress=on_progress)
                    await queue.put(
                        {
                            "type": "result",
                            "plan": json.loads(plan.model_dump_json()),
                            "meta": meta,
                        }
                    )
            except Exception as exc:
                await queue.put({"type": "error", "detail": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield sse_event(item, event=item.get("type"))
        finally:
            await task

    return StreamingResponse(event_stream(), media_type="text/event-stream")