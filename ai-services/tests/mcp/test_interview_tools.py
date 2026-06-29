from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.http_client import InterviewMCPBackend


@pytest.fixture()
def backend():
    return InterviewMCPBackend()


@pytest.mark.asyncio
async def test_get_interview_context():
    sample = {
        "id": "itv-test01",
        "candidate_name": "Huy",
        "plan": {"interview_brief": "Ask about Python."},
        "status": "in_progress",
    }
    with patch("app.mcp.interview_tools._backend.get_interview", AsyncMock(return_value=sample)) as mock_get:
        from app.mcp.interview_tools import get_interview_context

        result = await get_interview_context("itv-test01")
    assert result["candidate_name"] == "Huy"
    mock_get.assert_awaited_once_with("itv-test01")


@pytest.mark.asyncio
async def test_switch_mode_validates_mode():
    from app.mcp.interview_tools import switch_mode

    with pytest.raises(ValueError, match="interview.*code"):
        await switch_mode("itv-x", "invalid")


@pytest.mark.asyncio
async def test_switch_mode_calls_backend():
    with patch.object(InterviewMCPBackend, "switch_mode", AsyncMock(return_value={"mode": "code"})):
        from app.mcp.interview_tools import switch_mode

        result = await switch_mode("itv-x", "code")
    assert result["mode"] == "code"


@pytest.mark.asyncio
async def test_append_transcript_turn_validates_role():
    from app.mcp.interview_tools import append_transcript_turn

    with pytest.raises(ValueError, match="agent.*candidate"):
        await append_transcript_turn("itv-x", "moderator", "hello")


@pytest.mark.asyncio
async def test_append_transcript_turn_calls_backend():
    with patch.object(
        InterviewMCPBackend,
        "append_transcript_turn",
        AsyncMock(return_value=None),
    ) as mock_append:
        from app.mcp.interview_tools import append_transcript_turn

        result = await append_transcript_turn("itv-x", "agent", "Hello there", ts=1.0)
    assert result == {"ok": True}
    mock_append.assert_awaited_once_with(
        "itv-x",
        role="agent",
        content="Hello there",
        ts=1.0,
    )