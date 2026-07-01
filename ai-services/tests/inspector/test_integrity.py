import asyncio

from app.agents.inspector.agent import InspectorAgent
from app.agents.inspector.integrity import summarize_integrity
from app.schemas.api.inspector import InspectorEvaluateRequest


def test_summarize_integrity_high_risk():
    summary = summarize_integrity(
        [
            {"kind": "tab_switch", "severity": "high", "ts": 1.0},
            {"kind": "tab_switch", "severity": "high", "ts": 50.0},
            {"kind": "gaze_away", "severity": "medium", "ts": 100.0},
        ]
    )
    assert summary.risk in ("medium", "high")
    assert summary.total_violations >= 2


def test_inspector_includes_integrity_block():
    agent = InspectorAgent()
    request = InspectorEvaluateRequest(
        interview_id="itv-test01",
        candidate_name="Test User",
        position="Engineer",
        proctoring_events=[
            {"kind": "tab_switch", "severity": "high", "ts": 1.0},
            {"kind": "tab_switch", "severity": "high", "ts": 2.0},
        ],
        plan={"competencies": [{"name": "Communication", "weight": 100}]},
    )
    report, meta = asyncio.run(agent.run(request))
    assert "integrity" in report
    assert report["integrity"]["total_violations"] >= 1
    assert meta["agent"] == "inspector"
    assert meta.get("pdf_base64")