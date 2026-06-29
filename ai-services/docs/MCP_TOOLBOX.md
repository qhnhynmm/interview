# MCP Toolbox — Aurelia Interview Platform

## Architecture

```text
Interview Agent Worker (LiveKit)
        │  MCPServerHTTP (SSE)
        ▼
┌─────────────────────────────────────────────────────────┐
│  AI Services :8001                                      │
│  REST (HR/backend):  /api/v1/planning|assignment|...    │
│  MCP Interview:      /mcp/sse          (14 tools)       │
│  MCP Assignment:     /assignment-mcp/sse (3 tools)      │
│  Dev HTTP shim:      POST /mcp-http/tools/call          │
└───────────────────────────┬─────────────────────────────┘
                            │ httpx + X-Service-Key
                            ▼
                 Backend /api/v1/interviews/...
                            │
                            ▼
                      Postgres (source of truth)
```

## Tool → Backend mapping

### Interview MCP (`/mcp`)

| Tool | Method | Backend path | Auth |
|------|--------|--------------|------|
| `list_active_interviews` | GET | `/interviews/active` | Service |
| `get_interview_context` | GET | `/interviews/{id}` | Public |
| `get_transcript` | GET | `/interviews/{id}/transcript` | Service |
| `get_problem_statement` | GET | `/interviews/{id}` (extract) | Public |
| `get_live_snapshot` | GET | `/interviews/{id}` + `/transcript` | Mixed |
| `get_sandbox_files` | GET | `/interviews/{id}` | Public |
| `get_candidate_code` | GET | `/interviews/{id}` | Public |
| `get_code_run_logs` | GET | `/interviews/{id}` | Public |
| `analyze_candidate_code` | — | inline LLM in ai-services | — |
| `switch_mode` | POST | `/interviews/{id}/switch-mode` | Service |
| `append_transcript_turn` | POST | `/interviews/{id}/transcript/append` | Service |
| `send_message_to_candidate` | POST | `/interviews/{id}/send-agent-message` | Service |
| `set_coding_assistant` | POST | `/interviews/{id}/set-assistant` | Service |
| `end_interview` | POST | `/interviews/{id}/end` | Public |

### Assignment MCP (`/assignment-mcp`)

| Tool | Method | Backend path |
|------|--------|--------------|
| `enable_coding_assistant` | POST | `/interviews/{id}/set-assistant` |
| `disable_coding_assistant` | POST | `/interviews/{id}/set-assistant` |
| `get_coding_assistant_status` | GET | `/interviews/{id}/coding-assistant` |

## Agent tool decision guide

| Phase | Tool | When |
|-------|------|------|
| Join room | `get_interview_context` | First call — load plan, assignment, language |
| Each spoken turn | `append_transcript_turn` | After agent or candidate speaks |
| On-screen hint | `send_message_to_candidate` | Written UI text (not TTS) |
| Start coding | `switch_mode('code')` | After voice Q&A |
| Explain problem | `get_problem_statement` | Right after code mode — paraphrase, don't read raw |
| During coding | `get_candidate_code` / `get_sandbox_files` | Poll every few seconds |
| After test run | `get_code_run_logs` | Candidate clicked Run |
| Before follow-up | `analyze_candidate_code` | Grounded question from actual code |
| Back to voice | `switch_mode('interview')` | Wrap-up (skip if `finished: true`) |
| End session | `end_interview` | Once, after verbal goodbye |
| Project + AI help | `enable_coding_assistant` | Assignment MCP or `set_coding_assistant` |
| DSA unaided | `disable_coding_assistant` | Before coding phase |

## LiveKit worker wiring

```python
from livekit.agents import Agent, AgentSession, mcp as lk_mcp
from app.infra.mcp_client import build_mcp_servers
from app.config import get_settings

settings = get_settings()
mcp_servers = build_mcp_servers(settings)

agent = Agent(
    instructions="...",
    llm=realtime_model,
    mcp_servers=mcp_servers,
)
session = AgentSession(llm=realtime_model, mcp_servers=mcp_servers)
```

Env:

```bash
MCP_SSE_URL=http://127.0.0.1:8001/mcp/sse
INTERNAL_SERVICE_KEY=your-shared-secret
BACKEND_URL=http://127.0.0.1:8000
```

## Dev fallback (no SSE)

```bash
curl -X POST http://localhost:8001/mcp-http/tools/call \
  -H 'Content-Type: application/json' \
  -d '{"name":"get_interview_context","arguments":{"interview_id":"itv-xxx"}}'
```