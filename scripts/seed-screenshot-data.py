#!/usr/bin/env python3
"""Seed an interview with demo report/transcript for README screenshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.interview import Interview, InterviewStatus  # noqa: E402


def _demo_report(name: str, position: str) -> dict:
    return {
        "overall_score": 4.2,
        "max_score": 5,
        "headline": "Strong technical fundamentals with clear communication.",
        "recommendation": "hire",
        "candidate_name": name,
        "position": position,
        "competency_scores": [
            {"competency": "Technical depth", "weight": 0.35, "score": 4.5},
            {"competency": "Problem solving", "weight": 0.30, "score": 4.0},
            {"competency": "Communication", "weight": 0.20, "score": 4.0},
            {"competency": "System design", "weight": 0.15, "score": 3.5},
        ],
        "interview_summary": (
            "Candidate explained hash-map approach for Two Sum with correct complexity analysis. "
            "Voice answers were structured; coding submission passed core test cases."
        ),
        "integrity": {"risk": "low", "note": "No significant proctoring incidents."},
    }


def _demo_transcript() -> list[dict]:
    return [
        {
            "role": "agent",
            "content": "Xin chào! Hãy giới thiệu ngắn gọn về kinh nghiệm backend của bạn.",
            "ts": 1_700_000_000.0,
        },
        {
            "role": "candidate",
            "content": "Em có 5 năm làm Python/FastAPI, tập trung API scale và PostgreSQL.",
            "ts": 1_700_000_030.0,
        },
        {
            "role": "agent",
            "content": "Tốt. Bây giờ chuyển sang phần coding — implement Two Sum với hash map.",
            "ts": 1_700_000_090.0,
        },
        {
            "role": "candidate",
            "content": "Em duyệt mảng một lần, lưu complement trong dict, O(n) time.",
            "ts": 1_700_000_150.0,
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interview-id", required=True)
    parser.add_argument("--mode", choices=["completed", "code"], default="completed")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        row = db.get(Interview, args.interview_id)
        if row is None:
            raise SystemExit(f"Interview not found: {args.interview_id}")

        if args.mode == "code":
            row.ui_mode = "code"
            row.status = InterviewStatus.in_progress
            if not row.assignment:
                row.assignment = {
                    "type": "coding",
                    "coding": {
                        "mode": "dsa",
                        "title": "Two Sum",
                        "difficulty": "easy",
                        "statement": (
                            "Given an array `nums` and integer `target`, return indices of "
                            "two numbers that add up to `target`."
                        ),
                        "function_name": "two_sum",
                        "starter_code": "def two_sum(nums: list[int], target: int) -> list[int]:\n    pass\n",
                        "test_cases": [
                            {"label": "Basic", "inputs": [[2, 7, 11, 15], 9], "expected": [0, 1]},
                        ],
                        "ai_assistant_enabled": False,
                    },
                }
            row.current_code = row.current_code or (
                "def two_sum(nums: list[int], target: int) -> list[int]:\n"
                "    seen = {}\n"
                "    for i, n in enumerate(nums):\n"
                "        if target - n in seen:\n"
                "            return [seen[target - n], i]\n"
                "        seen[n] = i\n"
                "    return []\n"
            )
        else:
            row.status = InterviewStatus.completed
            row.ui_mode = "interview"
            row.report = _demo_report(row.candidate_name, row.position)
            row.conversation_history = _demo_transcript()
            row.assignment_finished = True

        db.add(row)
        db.commit()
        print(f"Seeded {args.interview_id} ({args.mode})")
    finally:
        db.close()


if __name__ == "__main__":
    main()