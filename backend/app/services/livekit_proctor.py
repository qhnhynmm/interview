"""Broadcast proctoring violations to the LiveKit interview room."""

from __future__ import annotations

import json
import logging

from app.config import Settings, get_settings
from app.services.livekit_tokens import _livekit_http_url

logger = logging.getLogger(__name__)


async def broadcast_proctor_violation(
    *,
    room_name: str,
    event: dict,
    settings: Settings | None = None,
) -> None:
    """Send a reliable data message to all participants in the interview room."""
    cfg = settings or get_settings()
    if not cfg.livekit_api_key or not cfg.livekit_api_secret:
        logger.debug("LiveKit not configured — skip proctor broadcast for room %s", room_name)
        return

    payload = {
        "type": "proctor:violation",
        "kind": event.get("kind", ""),
        "severity": event.get("severity", "medium"),
        "detail": event.get("detail", ""),
        "ts": event.get("ts"),
    }
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")

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
                    topic="proctor",
                )
            )
            logger.info(
                "Proctor violation broadcast room=%s kind=%s",
                room_name,
                payload["kind"],
            )
        finally:
            await lkapi.aclose()
    except Exception as exc:
        logger.warning("Proctor broadcast failed for room %s: %s", room_name, exc)