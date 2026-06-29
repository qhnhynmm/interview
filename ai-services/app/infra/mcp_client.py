"""Build LiveKit MCPServerHTTP clients for the interview worker."""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings


def build_mcp_servers(settings: Settings | None = None) -> list[Any]:
    """Return MCPServerHTTP instances for AgentSession / Agent wiring."""
    cfg = settings or get_settings()
    try:
        from livekit.agents import mcp as lk_mcp
    except ImportError as exc:
        raise RuntimeError("livekit-agents MCP support is required for the interview worker") from exc

    servers: list[Any] = []
    interview_url = cfg.mcp_sse_url.rstrip("/")
    if interview_url:
        servers.append(lk_mcp.MCPServerHTTP(url=interview_url))

    assignment_url = getattr(cfg, "mcp_assignment_sse_url", "").strip()
    if assignment_url:
        servers.append(lk_mcp.MCPServerHTTP(url=assignment_url))

    return servers