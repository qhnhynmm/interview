from app.agents.interview.session import InterviewSession
from app.agents.interview.voice_pipeline import VoicePipeline
from app.config import Settings


def test_voice_pipeline_greeting_and_instructions():
    session = InterviewSession(
        interview_id="itv-test01",
        language="en",
        plan={
            "candidate_name": "Huy",
            "position": "AI Engineer",
            "interview_brief": "Focus on Python and system design.",
            "duration_minutes": 50,
            "special_requirements": "Probe Redis caching",
            "competencies": [{"name": "Technical depth", "weight": 0.4}],
        },
    )
    pipeline = VoicePipeline(session)

    greeting = pipeline.greeting_text()
    assert "Huy" in greeting

    instructions = pipeline.system_instructions()
    assert "Focus on Python and system design." in instructions
    assert "Huy" in instructions
    assert "append_transcript_turn" in instructions
    assert "switch_mode" in instructions
    assert "Probe Redis caching" in instructions
    assert "50 minutes" in instructions


def test_vietnamese_fallback_brief_when_empty():
    session = InterviewSession(
        interview_id="itv-vi",
        language="vi",
        plan={"candidate_name": "Lan", "position": "Backend Engineer"},
    )
    instructions = VoicePipeline(session).system_instructions()
    assert "Lan" in instructions
    assert "project kỹ thuật" in instructions or "Phỏng vấn" in instructions


def test_build_realtime_model_requires_gemini_key():
    session = InterviewSession(interview_id="itv-test02", language="en", plan={})
    settings = Settings(GEMINI_API_KEY="")
    pipeline = VoicePipeline(session, settings)
    try:
        pipeline.build_realtime_model()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "GEMINI_API_KEY" in str(exc)
    assert raised


def test_build_realtime_model_uses_config():
    session = InterviewSession(
        interview_id="itv-test03",
        language="en",
        plan={"candidate_name": "Huy", "position": "AI Engineer", "interview_brief": "Ask about ML."},
    )
    settings = Settings(
        GEMINI_API_KEY="test-key",
        interview_live_model="gemini-2.5-flash-native-audio-preview-12-2025",
        interview_live_voice="Kore",
        interview_language="vi",
    )
    pipeline = VoicePipeline(session, settings)
    model = pipeline.build_realtime_model()
    assert model is not None


def test_build_realtime_model_uses_session_language_not_global_config():
    session = InterviewSession(interview_id="itv-test04", language="vi", plan={})
    settings = Settings(
        GEMINI_API_KEY="test-key",
        interview_live_model="gemini-2.5-flash-native-audio-preview-12-2025",
        interview_live_voice="Kore",
        interview_language="en",
    )
    pipeline = VoicePipeline(session, settings)
    model = pipeline.build_realtime_model()
    assert model._opts.language == "vi-VN"


def test_resolve_interview_language_from_backend_payload():
    from app.agents.interview.voice_pipeline import _resolve_interview_language

    assert _resolve_interview_language({"language": "vi"}, "en") == "vi"
    assert _resolve_interview_language({}, "en") == "en"


def test_build_realtime_model_uses_session_voice():
    session = InterviewSession(interview_id="itv-voice", language="en", voice="Kore", plan={})
    settings = Settings(
        GEMINI_API_KEY="test-key",
        interview_live_model="gemini-2.5-flash-native-audio-preview-12-2025",
        interview_live_voice="Puck",
    )
    pipeline = VoicePipeline(session, settings)
    model = pipeline.build_realtime_model()
    assert model._opts.voice == "Kore"


def test_resolve_interview_voice_from_backend_payload():
    from app.agents.interview.voice_pipeline import _resolve_interview_voice

    assert _resolve_interview_voice({"voice": "Aoede"}, "Puck") == "Aoede"
    assert _resolve_interview_voice({}, "Puck") == "Puck"