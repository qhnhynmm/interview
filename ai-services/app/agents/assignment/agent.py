import asyncio
import json
import logging
import re
from typing import Any

from agent_framework.openai import OpenAIChatCompletionClient

from app.agents.assignment.domain.directive import (
    default_directive,
    infer_domain_and_level,
    parse_assignment_directive,
)
from app.agents.assignment.domain.fallbacks import (
    build_dsa_assignment,
    build_fallback_assignment,
)
from app.agents.assignment.domain.normalize import _STYLES_IMPORT_RE, normalize_assignment
from app.agents.assignment.domain.prompts import build_user_prompt, system_instructions
from app.agents.assignment.domain.tools import search_problem_bank
from app.config import Settings, get_settings
from app.infra.progress import ProgressFn
from app.schemas.assignment import Assignment, AssignmentRequest
from app.schemas.plan import AssignmentDirective
from app.skills.interview_planning.scripts.planning_tools import search_problem_bank as get_bank_entry

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _extract_json_object(text: str) -> str:
    cleaned = _strip_json_fences(text)
    if cleaned.startswith("{"):
        return cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def parse_assignment_json(raw: str) -> Assignment:
    blob = _extract_json_object(raw)
    return Assignment.model_validate_json(blob)


def _validate_assignment_rules(assignment: Assignment, directive: AssignmentDirective) -> None:
    if assignment.type.value != directive.type:
        raise ValueError(f"type mismatch: expected {directive.type}, got {assignment.type}")
    if directive.type == "coding" and assignment.coding:
        if directive.mode == "dsa" and assignment.coding.starter_files:
            raise ValueError("DSA mode must have empty starter_files")
        if directive.mode == "project":
            if "App.js" not in assignment.coding.starter_files:
                raise ValueError("PROJECT mode requires App.js in starter_files")
            app_js = assignment.coding.starter_files["App.js"]
            if not _STYLES_IMPORT_RE.search(app_js):
                raise ValueError("App.js must import ./styles.css")
    if assignment.type.value == "cognitive" and assignment.cognitive:
        if len(assignment.cognitive.questions) != 10:
            raise ValueError("cognitive test must have 10 questions")


def _build_agent(settings: Settings, *, language: str = "en"):
    client = OpenAIChatCompletionClient(
        model=settings.assignment_model_effective,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    return client.as_agent(
        name="AssignmentAgent",
        instructions=system_instructions(language),
        tools=[search_problem_bank],
    )


async def _run_maf_once(req: AssignmentRequest, settings: Settings) -> str:
    agent = _build_agent(settings, language=req.language or "en")
    schema = json.dumps(Assignment.model_json_schema())
    prompt = (
        f"{build_user_prompt(req)}\n\n"
        f"Return ONLY one JSON object matching this schema (no prose, no markdown fence):\n{schema}"
    )
    timeout = settings.planning_request_timeout
    result: Any = await asyncio.wait_for(agent.run(prompt), timeout=timeout)
    text = getattr(result, "text", None) or str(result)
    return text.strip()


def _resolve_directive(req: AssignmentRequest) -> tuple[AssignmentDirective, Any]:
    resolved = infer_domain_and_level(
        position=req.position,
        jd_text=req.jd_text,
        cv_markdown=req.cv_markdown,
        level=req.level,
    )
    directive = parse_assignment_directive(req.assignment_brief) or default_directive(
        position=req.position,
        jd_text=req.jd_text,
        level=resolved.level,
    )
    if req.track == "nontech":
        directive = AssignmentDirective(
            type="cognitive", mode="dsa", ai_assistant=False, difficulty=directive.difficulty
        )
    if req.coding_mode in ("dsa", "project"):
        directive = AssignmentDirective(
            type="coding",
            mode=req.coding_mode,  # type: ignore[arg-type]
            ai_assistant=req.coding_mode == "project",
            difficulty=directive.difficulty,
        )
    return directive, resolved


async def _emit_progress(progress: ProgressFn | None, agent: str, text: str) -> None:
    if progress is not None:
        await progress(agent, text)


async def run_assignment_agent(
    req: AssignmentRequest,
    *,
    progress: ProgressFn | None = None,
) -> tuple[Assignment, dict]:
    settings = get_settings()
    directive, resolved = _resolve_directive(req)
    role = req.position or "the role"
    level = resolved.level or req.level or "Mid"
    await _emit_progress(
        progress,
        "Assignment",
        f"Directive received — designing a {level}-level task for {role}.",
    )
    meta: dict[str, Any] = {
        "agent": "assignment",
        "domain": resolved.domain,
        "level": resolved.level,
        "track": resolved.track,
        "directive": directive.model_dump(),
        "llm_enabled": settings.llm_enabled,
        "llm_used": False,
        "parse_attempts": 0,
    }

    # DSA: deterministic from verified problem bank (test_cases verbatim)
    if directive.type == "coding" and directive.mode == "dsa":
        await _emit_progress(progress, "Assignment", "Searching the problem bank for a difficulty reference…")
        entry = get_bank_entry(resolved.domain, resolved.level)  # type: ignore[arg-type]
        if entry is None:
            raise ValueError(f"No problem bank entry for {resolved.domain}/{resolved.level}")
        summary = f"DSA screening for {req.position or 'role'} — verifies algorithmic thinking without AI assist."
        assignment = build_dsa_assignment(entry=entry, directive=directive, summary=summary)
        meta["path"] = "deterministic-dsa"
        await _emit_progress(progress, "Assignment", "Assignment drafted and returned to Planning.")
        return assignment, meta

    if not settings.llm_enabled:
        await _emit_progress(
            progress,
            "Assignment",
            "Calibrating scope, time limit and AI-assistant policy…",
        )
        assignment = build_fallback_assignment(
            directive=directive,
            resolved=resolved,
            position=req.position or "Engineer",
            assignment_brief=req.assignment_brief,
        )
        meta["path"] = "fallback-no-llm"
        await _emit_progress(progress, "Assignment", "Assignment drafted and returned to Planning.")
        return assignment, meta

    await _emit_progress(
        progress,
        "Assignment",
        "Calibrating scope, time limit and AI-assistant policy…",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        meta["parse_attempts"] = attempt + 1
        try:
            raw = await _run_maf_once(req, settings)
            meta["llm_used"] = True
            assignment = parse_assignment_json(raw)
            assignment = normalize_assignment(assignment, directive)
            _validate_assignment_rules(assignment, directive)
            meta["path"] = "maf-llm"
            logger.info("assignment agent ok on attempt %d", attempt + 1)
            await _emit_progress(progress, "Assignment", "Assignment drafted and returned to Planning.")
            return assignment, meta
        except Exception as exc:
            last_error = exc
            logger.warning("assignment agent attempt %d failed: %s", attempt + 1, exc)

    logger.error("assignment agent failed after retries: %s", last_error)
    try:
        assignment = build_fallback_assignment(
            directive=directive,
            resolved=resolved,
            position=req.position or "Engineer",
            assignment_brief=req.assignment_brief,
        )
        meta["path"] = "fallback-after-llm-fail"
        meta["error"] = str(last_error)
        await _emit_progress(progress, "Assignment", "Assignment drafted and returned to Planning.")
        return assignment, meta
    except Exception as fallback_exc:
        raise ValueError(f"Assignment agent failed: {last_error}") from fallback_exc


class AssignmentAgent:
    async def run(self, request: AssignmentRequest) -> tuple[Assignment, dict]:
        return await run_assignment_agent(request)