from fastapi import APIRouter

from app.agents.coding_assistant.agent import CodingAssistantAgent
from app.schemas.api.coding_assistant import CodingAssistantRequest, CodingAssistantResponse

router = APIRouter(prefix="/coding-assistant", tags=["coding-assistant"])
_agent = CodingAssistantAgent()


@router.post("/chat", response_model=CodingAssistantResponse)
async def chat(body: CodingAssistantRequest) -> CodingAssistantResponse:
    message, meta = await _agent.run(body)
    return CodingAssistantResponse(message=message, meta=meta)