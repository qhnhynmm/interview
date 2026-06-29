"""LiveKit access token minting, agent dispatch, and join-window validation."""

import json
import logging
import time
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import jwt

from app.config import Settings, get_settings
from app.models.interview import Interview, InterviewStatus

logger = logging.getLogger(__name__)

JoinRole = str  # candidate | agent


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def assert_join_allowed(row: Interview, *, now: datetime | None = None) -> None:
    """Raise HTTP 403/410 when outside the join window or terminal status."""
    moment = _as_utc(now or datetime.now(UTC))

    if row.status in (InterviewStatus.completed, InterviewStatus.cancelled, InterviewStatus.abandoned):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Interview session is no longer available")

    if row.scheduled_at is None:
        return

    settings = get_settings()
    start = _as_utc(row.scheduled_at)
    open_at = start - timedelta(minutes=settings.slot_open_buffer_minutes)
    close_at = start + timedelta(minutes=settings.session_window_minutes)

    if moment < open_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Interview room is not open yet",
        )
    if moment > close_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Interview session has expired",
        )


def _video_grants(*, room: str, role: JoinRole) -> dict:
    if role == "agent":
        return {
            "roomJoin": True,
            "room": room,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
            "agent": True,
        }
    return {
        "roomJoin": True,
        "room": room,
        "canPublish": True,
        "canSubscribe": True,
        "canPublishData": True,
    }


def mint_access_token(
    *,
    room_name: str,
    identity: str,
    display_name: str,
    role: JoinRole = "candidate",
    settings: Settings | None = None,
) -> str:
    cfg = settings or get_settings()
    if not cfg.livekit_api_key or not cfg.livekit_api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured on the server",
        )

    now = int(time.time())
    ttl = max(60, int(cfg.livekit_token_ttl))
    claims = {
        "iss": cfg.livekit_api_key,
        "sub": identity,
        "name": display_name,
        "nbf": now,
        "exp": now + ttl,
        "video": _video_grants(room=room_name, role=role),
    }
    token = jwt.encode(claims, cfg.livekit_api_secret, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def build_join_token_response(
    row: Interview,
    *,
    role: JoinRole = "candidate",
    settings: Settings | None = None,
) -> dict[str, str]:
    cfg = settings or get_settings()
    room_name = row.id

    if role == "agent":
        identity = f"agent-{cfg.livekit_agent_name}"
        display_name = cfg.livekit_agent_name
    else:
        identity = f"candidate-{row.id}"
        display_name = row.candidate_name or "Candidate"

    token = mint_access_token(
        room_name=room_name,
        identity=identity,
        display_name=display_name,
        role=role,
        settings=cfg,
    )
    return {
        "token": token,
        "livekit_url": cfg.livekit_public_url,
        "room_name": room_name,
    }


def mark_candidate_joined(row: Interview) -> bool:
    """Transition scheduled → in_progress on first candidate join."""
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
        return True
    return False


def _livekit_http_url(ws_url: str) -> str:
    return ws_url.replace("ws://", "http://").replace("wss://", "https://")


async def dispatch_interview_agent(
    *,
    room_name: str,
    interview_id: str,
    settings: Settings | None = None,
) -> None:
    """Ask LiveKit to assign the interview worker to this room."""
    cfg = settings or get_settings()
    if not cfg.livekit_api_key or not cfg.livekit_api_secret:
        return

    try:
        from livekit import api

        lkapi = api.LiveKitAPI(
            _livekit_http_url(cfg.livekit_url),
            cfg.livekit_api_key,
            cfg.livekit_api_secret,
        )
        try:
            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=cfg.livekit_agent_name,
                    room=room_name,
                    metadata=json.dumps({"interview_id": interview_id}),
                )
            )
            logger.info("Dispatched agent %s to room %s", cfg.livekit_agent_name, room_name)
        finally:
            await lkapi.aclose()
    except Exception as exc:
        logger.warning("Agent dispatch failed for room %s: %s", room_name, exc)