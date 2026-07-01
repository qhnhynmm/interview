from app.agents.planning.prompts import (
    assignment_brief_system,
    evaluation_brief_system,
    interview_brief_system,
)


def test_interview_brief_vietnamese_language_tag():
    prompt = interview_brief_system("vi")
    assert "INTERVIEW_LANGUAGE: vi" in prompt
    assert "Tiếng Việt" in prompt or "Viết CHỈ" in prompt


def test_evaluation_brief_hard_gate_section():
    prompt = evaluation_brief_system("en")
    assert "HARD GATE" in prompt
    assert "Integrity rules" in prompt


def test_assignment_brief_hr_priority():
    prompt = assignment_brief_system("en")
    assert "HR NOTES" in prompt or "skill_gaps" in prompt