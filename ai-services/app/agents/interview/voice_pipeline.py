"""LiveKit voice pipeline — Gemini Live API (native audio in/out)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from livekit import rtc
from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext
from livekit.plugins import google

from app.agents.interview.mcp_client import MCPClient
from app.agents.interview.proctoring import ProctoringHandler
from app.agents.interview.prompts import build_greeting, build_system_instructions, extract_interview_context
from app.agents.interview.session import InterviewSession
from app.config import Settings, get_settings
from app.infra.backend_client import BackendClient

logger = logging.getLogger(__name__)


def _resolve_interview_language(interview: dict[str, Any], fallback: str) -> str:
    raw = (interview.get("language") or "").strip()
    return raw or fallback


def _resolve_interview_voice(interview: dict[str, Any], fallback: str) -> str:
    raw = (interview.get("voice") or "").strip()
    return raw or fallback


def _gemini_language_code(language: str) -> str | None:
    lang = language.strip().lower()
    if lang in {"en", "english"}:
        return "en-US"
    if lang in {"vi", "vietnamese", "vn"}:
        return "vi-VN"
    if lang:
        return language
    return None


# livekit google plugin times out generate_reply after 5s; Gemini Live handshake can take longer.
_GEMINI_CONNECT_TIMEOUT_SEC = 30.0
_GREETING_MAX_ATTEMPTS = 3


async def _wait_for_gemini_ready(realtime: Any, timeout: float = _GEMINI_CONNECT_TIMEOUT_SEC) -> None:
    """Block until the Gemini Live WebSocket is connected (metrics_collected with acquire_time)."""
    rt_session = realtime.session()
    loop = asyncio.get_running_loop()
    ready = loop.create_future()

    def _on_metrics(_ev: Any) -> None:
        if not ready.done():
            ready.set_result(None)

    rt_session.on("metrics_collected", _on_metrics)
    try:
        await asyncio.wait_for(ready, timeout=timeout)
        logger.info("Gemini Live connected (%.1fs timeout budget)", timeout)
    except asyncio.TimeoutError:
        logger.warning("Gemini Live not ready after %.0fs — greeting may fail", timeout)
    finally:
        rt_session.off("metrics_collected", _on_metrics)


class VoicePipeline:
    def __init__(self, session: InterviewSession, settings: Settings | None = None) -> None:
        self.session = session
        self._settings = settings or get_settings()

    def system_instructions(self) -> str:
        return build_system_instructions(
            interview_brief=self.session.plan.get("interview_brief", ""),
            candidate_name=self.session.plan.get("candidate_name", ""),
            position=self.session.plan.get("position", ""),
            language=self.session.language,
        )

    def greeting_text(self) -> str:
        return build_greeting(
            candidate_name=self.session.plan.get("candidate_name", ""),
            position=self.session.plan.get("position", ""),
            language=self.session.language,
        )

    def build_realtime_model(self) -> Any:
        settings = self._settings
        api_key = settings.gemini_api_key.strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini Live voice agent")

        kwargs: dict[str, Any] = {
            "model": settings.interview_live_model,
            "voice": self.session.voice or settings.interview_live_voice,
            "api_key": api_key,
            "instructions": self.system_instructions(),
            "temperature": settings.interview_temperature,
            "max_output_tokens": settings.interview_max_tokens,
        }
        language_code = _gemini_language_code(self.session.language)
        if language_code:
            kwargs["language"] = language_code
        return google.realtime.RealtimeModel(**kwargs)

    async def publish_agent_message(self, room: rtc.Room, message: str) -> None:
        payload = json.dumps({"type": "ui:agent_message", "message": message}).encode("utf-8")
        await room.local_participant.publish_data(payload, reliable=True)

    async def run(self, ctx: JobContext) -> None:
        realtime = self.build_realtime_model()
        backend = BackendClient(self._settings)

        # Gemini Live uses server-side turn detection — allow_interruptions must be True.
        allow_interruptions = True

        agent = Agent(
            instructions=self.system_instructions(),
            llm=realtime,
            allow_interruptions=allow_interruptions,
        )
        session = AgentSession(
            llm=realtime,
            allow_interruptions=allow_interruptions,
            min_endpointing_delay=self._settings.silence_threshold_ms / 1000.0,
        )

        disconnected = asyncio.Event()

        async def _end_interview(*, reason: str, detail: str) -> None:
            try:
                await backend.end_interview(
                    self.session.interview_id,
                    reason=reason,
                    detail=detail,
                )
            except Exception:
                logger.exception("Failed to mark interview %s ended", self.session.interview_id)
            disconnected.set()

        proctor = ProctoringHandler(
            interview_id=self.session.interview_id,
            language=self.session.language,
            settings=self._settings,
            agent_session=session,
            end_callback=_end_interview,
        )
        proctor.attach(ctx.room)

        @ctx.room.on("disconnected")
        def _on_disconnect(*_args: Any) -> None:
            disconnected.set()

        await session.start(agent=agent, room=ctx.room)
        await _wait_for_gemini_ready(realtime)

        greeting = self.greeting_text()
        await self.publish_agent_message(ctx.room, greeting)
        logger.info(
            "Speaking greeting for interview %s (gemini-live, language=%s, voice=%s)",
            self.session.interview_id,
            self.session.language,
            self.session.voice,
        )
        # Gemini Live RealtimeModel does not support session.say() — use generate_reply.
        lang_note = (
            "Speak in Vietnamese only."
            if self.session.language.lower().startswith("vi")
            else "Speak in English only."
        )
        for attempt in range(1, _GREETING_MAX_ATTEMPTS + 1):
            try:
                speech = session.generate_reply(
                    instructions=f"Greet the candidate now. {lang_note} Say exactly: {greeting}",
                )
                await speech.wait_for_playout()
                break
            except Exception:
                if attempt >= _GREETING_MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "Greeting attempt %d/%d failed for %s — retrying",
                    attempt,
                    _GREETING_MAX_ATTEMPTS,
                    self.session.interview_id,
                    exc_info=True,
                )
                await asyncio.sleep(2)

        logger.info("Interview session active — proctoring listener on %s", self.session.interview_id)
        await disconnected.wait()


async def load_session(interview_id: str, settings: Settings | None = None) -> InterviewSession:
    cfg = settings or get_settings()
    mcp = MCPClient(cfg)
    interview = await mcp.get_interview_context(interview_id)
    plan_payload = {"plan": interview.get("plan") or {}}
    context = extract_interview_context(interview, plan_payload)
    language = _resolve_interview_language(interview, cfg.interview_language)
    voice = _resolve_interview_voice(interview, cfg.interview_live_voice)
    logger.info("Loaded interview %s with language=%s voice=%s", interview_id, language, voice)
    return InterviewSession(
        interview_id=interview_id,
        language=language,
        voice=voice,
        plan=context,
    )


async def entrypoint(ctx: JobContext) -> None:
    settings = get_settings()
    interview_id = ctx.room.name
    logger.info("Agent dispatched to room %s (gemini-live)", interview_id)

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    try:
        session = await load_session(interview_id, settings)
    except Exception:
        logger.exception("Failed to load interview context for %s — using minimal session", interview_id)
        session = InterviewSession(
            interview_id=interview_id,
            language=settings.interview_language,
            voice=settings.interview_live_voice,
        )

    pipeline = VoicePipeline(session, settings)
    await pipeline.run(ctx)