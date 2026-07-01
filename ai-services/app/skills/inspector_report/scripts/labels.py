"""Bilingual static labels for Inspector PDF / markdown."""

from __future__ import annotations

_L: dict[str, dict[str, str]] = {
    "en": {
        "report_title": "Interview Evaluation Report",
        "candidate": "Candidate",
        "position": "Position",
        "date": "Date",
        "overall_score": "Overall Score",
        "track": "Track",
        "integrity": "Integrity",
        "executive_summary": "Executive Summary",
        "competencies": "Competency Assessment",
        "coding_assessment": "Coding Assessment",
        "strengths": "Strengths",
        "concerns": "Concerns",
        "competency_detail": "Competency Detail",
        "competency_col": "Competency",
        "weight_col": "Weight",
        "score_col": "Score",
        "rationale_col": "Rationale",
        "integrity_section": "Proctoring Integrity",
        "next_steps": "Recommended Next Steps",
        "track_tech": "Technical",
        "track_nontech": "Non-Technical",
        "tests_passed": "Tests Passed",
        "risk_clean": "Clean",
        "risk_low": "Low",
        "risk_medium": "Medium",
        "risk_high": "High",
        "rec_strong_hire": "STRONG HIRE",
        "rec_hire": "HIRE",
        "rec_lean_hire": "LEAN HIRE",
        "rec_no_hire": "NO HIRE",
        "rec_strong_no_hire": "STRONG NO HIRE",
        "gauge_caption": "Weighted overall score (0–5 scale)",
        "radar_caption": "Competency profile across evaluation dimensions",
        "bar_caption": "Competency ranking",
        "coding_caption": "Coding dimension scores",
        "donut_caption": "Automated test pass rate",
    },
    "vi": {
        "report_title": "Báo cáo đánh giá phỏng vấn",
        "candidate": "Ứng viên",
        "position": "Vị trí",
        "date": "Ngày",
        "overall_score": "Điểm tổng",
        "track": "Hình thức",
        "integrity": "Toàn vẹn",
        "executive_summary": "Tóm tắt điều hành",
        "competencies": "Đánh giá năng lực",
        "coding_assessment": "Đánh giá coding",
        "strengths": "Điểm mạnh",
        "concerns": "Cần lưu ý",
        "competency_detail": "Chi tiết năng lực",
        "competency_col": "Năng lực",
        "weight_col": "Trọng số",
        "score_col": "Điểm",
        "rationale_col": "Lý do",
        "integrity_section": "Toàn vẹn proctoring",
        "next_steps": "Bước tiếp theo đề xuất",
        "track_tech": "Kỹ thuật",
        "track_nontech": "Phi kỹ thuật",
        "tests_passed": "Test đạt",
        "risk_clean": "Sạch",
        "risk_low": "Thấp",
        "risk_medium": "Trung bình",
        "risk_high": "Cao",
        "rec_strong_hire": "TUYỂN MẠNH",
        "rec_hire": "NÊN TUYỂN",
        "rec_lean_hire": "CÂN NHẮC TUYỂN",
        "rec_no_hire": "KHÔNG TUYỂN",
        "rec_strong_no_hire": "LOẠI MẠNH",
        "gauge_caption": "Điểm tổng có trọng số (thang 0–5)",
        "radar_caption": "Hồ sơ năng lực theo các chiều đánh giá",
        "bar_caption": "Xếp hạng năng lực",
        "coding_caption": "Điểm theo chiều coding",
        "donut_caption": "Tỷ lệ test tự động đạt",
    },
}


def labels(language: str) -> dict[str, str]:
    lang = "vi" if (language or "").startswith("vi") else "en"
    return _L[lang]


def recommendation_label(rec: str, language: str) -> str:
    L = labels(language)
    key = f"rec_{rec}"
    return L.get(key, rec.replace("_", " ").upper())