from app.agents.inspector.fallback import build_fallback_scorecard
from app.agents.inspector.integrity import summarize_integrity
from app.agents.inspector.plan_adapter import extract_plan_context
from app.schemas.inspector.evaluation import EvaluationRequest
from app.skills.inspector_report.scripts.pdf_builder import build_markdown, build_pdf


def test_build_pdf_and_markdown():
    req = EvaluationRequest(
        interview_id="itv-pdf01",
        candidate_name="Jane Doe",
        position="Backend Engineer",
        language="en",
        transcript=[{"role": "agent", "content": "Hello"}],
    )
    ctx = extract_plan_context({})
    integrity = summarize_integrity([])
    card = build_fallback_scorecard(req, ctx, integrity)
    pdf = build_pdf(card, integrity, "en")
    md = build_markdown(card, integrity, "en")
    assert pdf[:4] == b"%PDF"
    assert "Jane Doe" in md
    assert len(pdf) > 1000