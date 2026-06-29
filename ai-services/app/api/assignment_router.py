import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.assignment.agent import run_assignment_agent
from app.infra.sse import sse_event
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


@router.post("/generate/stream")
async def generate_assignment_stream(body: AssignmentRequest) -> StreamingResponse:
    """Assignment Agent with SSE progress events."""

    async def event_stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_progress(agent: str, text: str) -> None:
            await queue.put({"type": "progress", "agent": agent, "text": text})

        async def run() -> None:
            try:
                with trace_span(
                    "api.assignment.generate.stream",
                    kind="AGENT",
                    interview_id=body.interview_id,
                ):
                    assignment, meta = await run_assignment_agent(body, progress=on_progress)
                    await queue.put(
                        {
                            "type": "result",
                            "assignment": json.loads(assignment.model_dump_json()),
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