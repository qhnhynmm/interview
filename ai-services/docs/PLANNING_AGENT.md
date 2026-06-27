# Planning Agent — Design Summary

## Role

One-shot agent at interview link creation. Reads **CV markdown + JD + HR notes**, outputs **3 markdown briefs** for downstream agents. Does not interview, score, or generate concrete assignment problems.

## Pipeline

```text
PlanRequest
  │
  ├─ Step A (deterministic, plain Python)
  │    extract_requirements → match_skills → search_problem_bank
  │    → competencies (renormalized to 100%) → assignment directive
  │
  ├─ Step B (1× LLM JSON analyst, optional)
  │    overlay semantic facts; block coding→cognitive flip when JD has tech skills
  │
  └─ Step C (3× sequential LLM markdown briefs, optional)
       interview_brief → evaluation_brief → assignment_brief (+ directive header)
       any failure → deterministic fallback; HTTP 200 always
```

## Output contract

`InterviewPlan`: `interview_brief`, `evaluation_brief`, `assignment_brief` (separate markdown strings), `duration_minutes`, `source`, optional `grounding` snapshot.

## Dependencies

- **MAF** `OpenAIChatCompletionClient` → `/v1/chat/completions`
- `asyncio.Semaphore(2)` cross-request LLM cap
- `asyncio.wait_for(75s)` per call

## Extension points

| Module | Purpose |
|--------|---------|
| `skills/jd_analysis/scripts/jd_tools.py` | Taxonomy + JD parsing |
| `skills/interview_planning/scripts/planning_tools.py` | CV match, competencies, directive |
| `skills/interview_planning/scripts/problem_bank.py` | Difficulty reference problems |
| `agents/planning/fallbacks.py` | Degraded brief templates |
| `agents/planning/llm.py` | MAF wrapper |