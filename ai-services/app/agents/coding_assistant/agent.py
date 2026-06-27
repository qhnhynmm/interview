from app.agents.base import AgentBase
from app.config import get_settings
from app.schemas.api.coding_assistant import CodingAssistantRequest


class CodingAssistantAgent(AgentBase):
    name = "coding_assistant"

    async def run(self, request: CodingAssistantRequest) -> tuple[str, dict]:
        settings = get_settings()
        system = (
            "You are a concise coding assistant for a live interview. "
            "Give hints, not full solutions. Respond in the interview language."
        )
        messages = [{"role": "system", "content": system}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        if request.code.strip():
            messages.append({"role": "user", "content": f"Current code:\n```\n{request.code}\n```"})

        text = await self.llm.chat_text(
            model=settings.coding_assistant_model,
            messages=messages,
            temperature=settings.coding_assistant_temperature,
            max_tokens=settings.coding_assistant_max_tokens,
        )
        if text:
            return text, {"agent": self.name, "llm_used": True}

        last = request.messages[-1].content if request.messages else ""
        fallback = (
            "Try breaking the problem into smaller steps. "
            f"For your last question ({last[:80]}...), consider edge cases first."
        )
        return fallback, {"agent": self.name, "llm_used": False}