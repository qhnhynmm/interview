import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.mcp.tools import ALL_TOOLS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    name: str
    result: Any


@router.get("/tools")
def list_tools() -> dict[str, list[str]]:
    return {"tools": sorted(ALL_TOOLS.keys())}


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(body: ToolCallRequest) -> ToolCallResponse:
    fn = ALL_TOOLS.get(body.name)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {body.name}")
    try:
        result = await fn(**body.arguments)
    except Exception as exc:
        logger.exception("MCP tool %s failed", body.name)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ToolCallResponse(name=body.name, result=result)


@router.get("/sse")
async def mcp_sse_info() -> dict[str, str]:
    """SSE transport placeholder — swap for FastMCP when interview worker connects."""
    return {
        "transport": "sse",
        "status": "scaffold",
        "hint": "Use POST /mcp/tools/call during development",
    }


@router.post("/tools/call/raw")
async def call_tool_raw(body: ToolCallRequest) -> str:
    response = await call_tool(body)
    return json.dumps(response.model_dump())