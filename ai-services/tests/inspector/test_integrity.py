import asyncio

from app.agents.inspector.agent import InspectorAgent
from app.schemas.api.inspector import InspectorEvaluateRequest


def test_inspector_includes_integrity_block():
    agent = InspectorAgent()
    request = InspectorEvaluateRequest(
        interview_id="itv-test01",
        proctoring_events=[
            {"kind": "tab_switch", "severity": "high", "ts": 1.0},
            {"kind": "tab_switch", "severity": "high", "ts": 2.0},
        ],
        plan={"competencies": [{"name": "Communication"}]},
    )
    report, meta = asyncio.run(agent.run(request))
    assert "integrity" in report
    assert report["integrity"]["incident_count"] == 1
    assert meta["agent"] == "inspector"