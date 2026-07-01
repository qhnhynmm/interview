from app.agents.base import AgentBase
from app.agents.coding_assistant.prompts import build_system_prompt
from app.config import get_settings
from app.schemas.api.coding_assistant import CodingAssistantRequest


class CodingAssistantAgent(AgentBase):
    name = "coding_assistant"

    async def run(self, request: CodingAssistantRequest) -> tuple[str, dict]:
        settings = get_settings()
        system = build_system_prompt(
            language=request.language,
            position=getattr(request, "position", "") or "",
            assignment_title=getattr(request, "assignment_title", "") or "",
            assignment_mode=getattr(request, "assignment_mode", "") or "",
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
        if request.language.lower().startswith("vi"):
            fallback = (
                "Thử chia bài toán thành các bước nhỏ hơn. "
                f"Với câu hỏi gần nhất ({last[:80]}...), hãy xem xét edge case trước."
            )
        else:
            fallback = (
                "Try breaking the problem into smaller steps. "
                f"For your last question ({last[:80]}...), consider edge cases first."
            )
        return fallback, {"agent": self.name, "llm_used": False}