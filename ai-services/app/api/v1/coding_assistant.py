from fastapi import APIRouter

from app.agents.coding_assistant.agent import CodingAssistantAgent
from app.infra.tracing import set_span_attributes, trace_span
from app.schemas.api.coding_assistant import CodingAssistantRequest, CodingAssistantResponse

router = APIRouter(prefix="/coding-assistant", tags=["coding-assistant"])
_agent = CodingAssistantAgent()


@router.post("/chat", response_model=CodingAssistantResponse)
async def chat(body: CodingAssistantRequest) -> CodingAssistantResponse:
    with trace_span(
        "api.coding_assistant.chat",
        kind="AGENT",
        agent="coding_assistant",
        interview_id=body.interview_id,
        message_count=len(body.messages),
    ):
        message, meta = await _agent.run(body)
        set_span_attributes(reply_chars=len(message or ""), llm_used=meta.get("llm_used"))
        return CodingAssistantResponse(message=message, meta=meta)