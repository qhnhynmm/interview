import asyncio
from unittest.mock import AsyncMock, MagicMock

from livekit.agents.llm import ChatMessage
from livekit.agents.voice.events import ConversationItemAddedEvent

from app.agents.interview.transcript_recorder import TranscriptRecorder


def test_transcript_recorder_maps_roles_and_dedupes():
    mcp = MagicMock()
    mcp.call = AsyncMock(return_value={"ok": True})
    recorder = TranscriptRecorder("itv-test", mcp)

    async def _run():
        user_msg = ChatMessage(role="user", content=["Hello from candidate"])
        agent_msg = ChatMessage(role="assistant", content=["Hi, welcome."])

        await recorder._handle_item(ConversationItemAddedEvent(item=user_msg))
        await recorder._handle_item(ConversationItemAddedEvent(item=user_msg))
        await recorder._handle_item(ConversationItemAddedEvent(item=agent_msg))

    asyncio.run(_run())

    assert mcp.call.await_count == 2
    first = mcp.call.await_args_list[0].kwargs
    second = mcp.call.await_args_list[1].kwargs
    assert first["role"] == "candidate"
    assert first["content"] == "Hello from candidate"
    assert second["role"] == "agent"
    assert second["content"] == "Hi, welcome."