# Assignment Agent — Design Summary

## Role

Second agent in the interview link pipeline. Runs **after** Planning Agent when HR creates a link. Reads **CV + JD + assignment_brief** (directive on line 1 from planning) and outputs one structured **`Assignment` JSON** — problem statement, starter code/files, and test cases. Does not interview, score, or generate interview plans.

## Pipeline position

```text
Planning Agent
        │
        ▼ (assignment_brief)
Assignment Agent
        │
        ▼
   Assignment JSON → Backend Postgres (interview.assignment)
        │
        ▼ (candidate joins)
   Interview Agent → code mode UI
        │
        ▼ (/end)
   Inspector Agent grades submission
```

## Decision workflow

| Step | Rule |
|------|------|
| 0 | Honor `ASSIGNMENT DIRECTIVE` first line of `assignment_brief` (type, mode, ai_assistant, difficulty) |
| 1 | Infer track: engineering → TECH (coding), sales/HR/marketing → NON-TECH (cognitive) |
| 2a | TECH + DSA: `search_problem_bank` → copy `test_cases` verbatim, `ai_assistant_enabled=false` |
| 2a | TECH + PROJECT: Sandpack React (JS only), `App.js` + `styles.css`, acceptance-criteria tests, AI on |
| 2b | NON-TECH: exactly 10 MCQ × 4 options, `answer` ∈ A–D |

## Execution paths

| Path | When | LLM |
|------|------|-----|
| `deterministic-dsa` | Directive → coding/dsa | No — problem bank |
| `maf-llm` | project or cognitive | MAF + `search_problem_bank` tool |
| `fallback-*` | LLM off or parse fail after 2 retries | Deterministic templates |

## API

- `POST /api/v1/assignment/generate`
- Request: `AssignmentRequest` — `interview_id`, CV, JD, `assignment_brief`, optional `track`/`coding_mode`/`level`
- Response: `{ assignment, meta }`

## Dependencies

- **MAF** `OpenAIChatCompletionClient` → `/v1/chat/completions` (no JSON response_format — avoids gateway truncation)
- 1 MAF tool: `search_problem_bank(domain, level)` — re-export from `planning_tools`
- Problem bank: `skills/interview_planning/scripts/problem_bank.py` (7 domain/level combos)

## Frontend mapping

| type | mode | UI |
|------|------|-----|
| coding | dsa | Monaco + Python test runner |
| coding | project | Sandpack React sandbox |
| cognitive | — | 10 MCQ A/B/C/D |

## Key modules

| Module | Purpose |
|--------|---------|
| `agents/assignment/agent.py` | `run_assignment_agent()`, JSON parse + validation |
| `agents/assignment/domain/directive.py` | Parse directive, infer track/domain/level |
| `agents/assignment/domain/prompts.py` | System instructions + user prompt |
| `agents/assignment/domain/fallbacks.py` | DSA/project/cognitive fallbacks |
| `schemas/assignment.py` | Pydantic contract (sync mirror in `backend/`) |