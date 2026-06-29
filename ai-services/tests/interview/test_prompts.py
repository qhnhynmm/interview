from app.agents.interview.prompts import build_greeting, build_system_instructions, extract_interview_context


def test_build_greeting_english():
    text = build_greeting(candidate_name="Huy", position="AI Engineer", language="en")
    assert "Huy" in text
    assert "Aurelia" in text


def test_build_greeting_vietnamese():
    text = build_greeting(candidate_name="Huy", position="AI Engineer", language="vi")
    assert "Huy" in text
    assert "Aurelia" in text
    assert "Xin chào" in text


def test_build_system_instructions_vietnamese():
    text = build_system_instructions(
        interview_brief="Hỏi về Python.",
        candidate_name="Huy",
        position="AI Engineer",
        language="vi",
    )
    assert "Vietnamese" in text
    assert "only in Vietnamese" in text


def test_build_system_instructions_uses_brief():
    brief = "## Topics\n- Python\n- React"
    text = build_system_instructions(
        interview_brief=brief,
        candidate_name="Huy",
        position="Backend Engineer",
        language="en",
    )
    assert brief in text
    assert "Huy" in text


def test_extract_interview_context_from_plan_payload():
    ctx = extract_interview_context(
        {"candidate_name": "Huy", "position": "AI Engineer"},
        {"plan": {"interview_brief": "Ask about ML.", "duration_minutes": 20}},
    )
    assert ctx["candidate_name"] == "Huy"
    assert ctx["interview_brief"] == "Ask about ML."
    assert ctx["duration_minutes"] == 20