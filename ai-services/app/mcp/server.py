"""Dev HTTP shim for MCP tools (POST /mcp-http/tools/call). Production uses FastMCP SSE."""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.infra.tracing import set_span_attributes, span_error, span_ok, trace_span
from app.mcp.assignment_tools import ASSIGNMENT_TOOL_REGISTRY
from app.mcp.interview_tools import INTERVIEW_TOOL_REGISTRY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp-http", tags=["mcp-http"])

ALL_TOOLS = {**INTERVIEW_TOOL_REGISTRY, **ASSIGNMENT_TOOL_REGISTRY}


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
    interview_id = body.arguments.get("interview_id")
    with trace_span(
        "mcp.tool",
        kind="TOOL",
        tool=body.name,
        interview_id=interview_id,
        argument_keys=sorted(body.arguments.keys()),
        arguments=body.arguments,
    ):
        fn = ALL_TOOLS.get(body.name)
        if fn is None:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {body.name}")
        try:
            result = await fn(**body.arguments)
        except Exception as exc:
            logger.exception("MCP tool %s failed", body.name)
            span_error(exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        set_span_attributes(
            success=bool(result) if isinstance(result, dict) else True,
            result=result,
        )
        span_ok()
        return ToolCallResponse(name=body.name, result=result)


@router.post("/tools/call/raw")
async def call_tool_raw(body: ToolCallRequest) -> str:
    response = await call_tool(body)
    return json.dumps(response.model_dump())