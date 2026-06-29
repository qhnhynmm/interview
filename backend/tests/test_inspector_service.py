from app.models.interview import Interview, InterviewStatus
from app.services.inspector import normalize_report


def test_normalize_report_shapes_competency_list():
    row = Interview(
        id="itv-abc12345",
        created_by_id=1,
        candidate_name="Jane Doe",
        candidate_email="jane@email.com",
        position="Engineer",
        jd_text="JD",
        status=InterviewStatus.completed,
        plan={
            "competencies": [
                {"name": "Technical depth", "weight": 0.6},
                {"name": "Communication", "weight": 0.4},
            ]
        },
    )
    raw = {
        "overall_score": 4.0,
        "competency_scores": {"Technical depth": 4.2, "Communication": 3.5},
        "summary": "Solid performance.",
    }
    report = normalize_report(row, raw)
    assert report["candidate_name"] == "Jane Doe"
    assert report["interview_summary"] == "Solid performance."
    assert len(report["competency_scores"]) == 2
    assert report["competency_scores"][0]["competency"] == "Technical depth"
    assert report["competency_scores"][0]["weight"] == 0.6