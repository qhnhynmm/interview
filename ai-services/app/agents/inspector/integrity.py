"""Deterministic integrity scoring from proctoring event logs."""

from __future__ import annotations

from typing import Any

# Penalty weight per incident (deduped) by violation kind.
_KIND_WEIGHTS: dict[str, int] = {
    "tab_switch": 12,
    "gaze_away": 8,
    "multiple_faces": 18,
    "phone_detected": 22,
    "secondary_monitor": 16,
}

# Events within this window with the same kind count as one incident.
_DEDUP_WINDOW_SEC = 45.0


def _is_violation(event: dict[str, Any]) -> bool:
    kind = str(event.get("kind") or "")
    severity = str(event.get("severity") or "medium")
    if kind == "detection_unsupported" or severity == "info":
        return False
    return kind in _KIND_WEIGHTS


def dedupe_incidents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse repeat browser reports into distinct incidents."""
    violations = [e for e in events if _is_violation(e)]
    violations.sort(key=lambda e: float(e.get("ts") or 0))

    incidents: list[dict[str, Any]] = []
    last_by_kind: dict[str, float] = {}

    for event in violations:
        kind = str(event.get("kind") or "")
        ts = float(event.get("ts") or 0)
        prev = last_by_kind.get(kind)
        if prev is not None and ts - prev < _DEDUP_WINDOW_SEC:
            continue
        last_by_kind[kind] = ts
        incidents.append(event)

    return incidents


def compute_integrity(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a deterministic integrity block for the HR report."""
    incidents = dedupe_incidents(events)
    by_kind: dict[str, int] = {}
    penalty = 0
    for event in incidents:
        kind = str(event.get("kind") or "")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        penalty += _KIND_WEIGHTS.get(kind, 10)

    score = max(0, 100 - penalty)
    if score >= 85:
        band = "high"
        flag = False
    elif score >= 65:
        band = "medium"
        flag = False
    elif score >= 40:
        band = "low"
        flag = True
    else:
        band = "critical"
        flag = True

    unsupported = [
        e for e in events
        if str(e.get("kind")) == "detection_unsupported"
    ]

    return {
        "integrity_score": score,
        "integrity_band": band,
        "integrity_flag": flag,
        "incident_count": len(incidents),
        "incidents_by_kind": by_kind,
        "total_raw_events": len(events),
        "unsupported_checks": len(unsupported),
        "method": "deterministic_v1",
    }