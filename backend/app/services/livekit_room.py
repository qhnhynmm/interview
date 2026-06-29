"""Broadcast UI/control messages to LiveKit interview rooms."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings, get_settings
from app.services.livekit_tokens import _livekit_http_url

logger = logging.getLogger(__name__)


async def broadcast_room_data(
    *,
    room_name: str,
    payload: dict[str, Any],
    topic: str = "",
    settings: Settings | None = None,
) -> bool:
    """Send a reliable data packet to all participants in the room."""
    cfg = settings or get_settings()
    if not cfg.livekit_api_key or not cfg.livekit_api_secret:
        logger.debug("LiveKit not configured — skip broadcast for room %s", room_name)
        return False

    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    try:
        from livekit import api
        from livekit.protocol.models import DataPacket

        lkapi = api.LiveKitAPI(
            _livekit_http_url(cfg.livekit_url),
            cfg.livekit_api_key,
            cfg.livekit_api_secret,
        )
        try:
            await lkapi.room.send_data(
                api.SendDataRequest(
                    room=room_name,
                    data=data,
                    kind=DataPacket.Kind.RELIABLE,
                    topic=topic,
                )
            )
            logger.info("Room data broadcast room=%s type=%s", room_name, payload.get("type"))
            return True
        finally:
            await lkapi.aclose()
    except Exception as exc:
        logger.warning("Room broadcast failed for %s: %s", room_name, exc)
        return False