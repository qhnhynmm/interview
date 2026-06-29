from app.agents.inspector.integrity import compute_integrity, dedupe_incidents
from app.agents.interview.proctoring import escalation_tier, warning_text


def test_escalation_tiers():
    assert escalation_tier(1) == 1
    assert escalation_tier(2) == 1
    assert escalation_tier(3) == 2
    assert escalation_tier(5) == 3


def test_warning_text_en_tab_switch():
    assert "interview window" in warning_text(language="en", kind="tab_switch", tier=1).lower()


def test_warning_text_vi_phone():
    text = warning_text(language="vi", kind="phone_detected", tier=2)
    assert "điện thoại" in text.lower()


def test_dedupe_incidents_same_kind():
    events = [
        {"kind": "tab_switch", "severity": "high", "ts": 10.0},
        {"kind": "tab_switch", "severity": "high", "ts": 12.0},
        {"kind": "tab_switch", "severity": "high", "ts": 60.0},
    ]
    incidents = dedupe_incidents(events)
    assert len(incidents) == 2


def test_compute_integrity_penalizes_violations():
    events = [
        {"kind": "phone_detected", "severity": "high", "ts": 1.0},
        {"kind": "tab_switch", "severity": "high", "ts": 50.0},
        {"kind": "detection_unsupported", "severity": "info", "ts": 2.0},
    ]
    result = compute_integrity(events)
    assert result["incident_count"] == 2
    assert result["integrity_score"] < 100
    assert result["incidents_by_kind"]["phone_detected"] == 1
    assert result["unsupported_checks"] == 1