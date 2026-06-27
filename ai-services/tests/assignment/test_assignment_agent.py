import pytest

from app.agents.assignment.agent import parse_assignment_json, run_assignment_agent
from app.agents.assignment.domain.normalize import normalize_assignment, normalize_project_coding
from app.schemas.assignment import Assignment, AssignmentType, CodingChallenge, CodingMode
from app.agents.assignment.domain.directive import parse_assignment_directive
from app.agents.assignment.domain.fallbacks import build_dsa_assignment, build_cognitive_assignment
from app.schemas.assignment import AssignmentRequest
from app.schemas.plan import AssignmentDirective
from app.skills.interview_planning.scripts.planning_tools import search_problem_bank, search_problem_bank_list


DIRECTIVE_DSA = (
    "ASSIGNMENT DIRECTIVE → type: coding · mode: dsa · ai_assistant: disabled · difficulty: easy\n\n"
    "Probe Python fundamentals."
)

DIRECTIVE_PROJECT = (
    "ASSIGNMENT DIRECTIVE → type: coding · mode: project · ai_assistant: enabled · difficulty: hard\n\n"
    "Build a streaming UI."
)


def test_parse_assignment_directive():
    d = parse_assignment_directive(DIRECTIVE_DSA)
    assert d is not None
    assert d.type == "coding"
    assert d.mode == "dsa"
    assert d.ai_assistant is False
    assert d.difficulty == "easy"


def test_problem_bank_seven_combinations():
    combos = [
        ("backend", "junior"),
        ("backend", "mid"),
        ("backend", "senior"),
        ("ai", "mid"),
        ("frontend", "mid"),
        ("data", "mid"),
        ("devops", "mid"),
    ]
    for domain, level in combos:
        assert search_problem_bank(domain, level) is not None  # type: ignore[arg-type]


def test_search_problem_bank_list_returns_dicts():
    rows = search_problem_bank_list("backend", "junior")
    assert rows
    assert "test_cases" in rows[0]
    assert rows[0]["title"] == "Two Sum"


def test_dsa_test_cases_verbatim():
    entry = search_problem_bank("backend", "junior")  # type: ignore[arg-type]
    directive = AssignmentDirective(type="coding", mode="dsa", ai_assistant=False, difficulty="easy")
    assignment = build_dsa_assignment(entry=entry, directive=directive)
    bank_cases = entry.test_cases
    for i, tc in enumerate(assignment.coding.test_cases):  # type: ignore[union-attr]
        assert tc.label == bank_cases[i]["label"]
        assert tc.inputs == bank_cases[i]["inputs"]
        assert tc.expected == bank_cases[i]["expected"]
    assert assignment.coding.ai_assistant_enabled is False  # type: ignore[union-attr]


def test_cognitive_ten_questions():
    assignment = build_cognitive_assignment(position="Marketing Manager")
    assert assignment.type.value == "cognitive"
    assert len(assignment.cognitive.questions) == 10  # type: ignore[union-attr]
    for q in assignment.cognitive.questions:  # type: ignore[union-attr]
        assert len(q.options) == 4
        assert q.answer in {"A", "B", "C", "D"}


def test_normalize_project_injects_styles_import():
    coding = CodingChallenge(
        mode=CodingMode.project,
        title="Chat UI",
        statement="Build a chat",
        starter_code="import { useState } from 'react';\nexport default function App() { return null; }",
        starter_files={"App.js": "import { useState } from 'react';\nexport default function App() { return null; }"},
        test_cases=[],
        ai_assistant_enabled=True,
    )
    fixed = normalize_project_coding(coding)
    assert "./styles.css" in fixed.starter_files["App.js"]
    assert fixed.starter_code == fixed.starter_files["App.js"]
    assert "styles.css" in fixed.starter_files
    assert len(fixed.test_cases) >= 2


def test_normalize_assignment_enforces_directive():
    assignment = Assignment(
        type=AssignmentType.coding,
        summary="test",
        coding=CodingChallenge(
            mode=CodingMode.dsa,
            title="UI",
            statement="x",
            starter_code="code",
            starter_files={"App.js": "x"},
            ai_assistant_enabled=False,
        ),
    )
    directive = AssignmentDirective(
        type="coding", mode="project", ai_assistant=True, difficulty="hard"
    )
    fixed = normalize_assignment(assignment, directive)
    assert fixed.coding.mode.value == "project"  # type: ignore[union-attr]
    assert fixed.coding.ai_assistant_enabled is True  # type: ignore[union-attr]
    assert fixed.coding.difficulty == "hard"  # type: ignore[union-attr]
    assert "./styles.css" in fixed.coding.starter_files["App.js"]  # type: ignore[union-attr]


def test_parse_assignment_json():
    raw = """{
      "type": "coding",
      "summary": "test",
      "coding": {
        "mode": "dsa",
        "title": "Two Sum",
        "difficulty": "easy",
        "statement": "sum",
        "function_name": "two_sum",
        "starter_code": "pass",
        "starter_files": {},
        "test_cases": [{"label": "A", "inputs": [[1,2], 3], "expected": [0,1]}],
        "ai_assistant_enabled": false,
        "allowed_resources": []
      },
      "cognitive": null
    }"""
    a = parse_assignment_json(raw)
    assert a.type.value == "coding"
    assert a.coding.mode.value == "dsa"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_run_assignment_dsa_junior_backend():
    assignment, meta = await run_assignment_agent(
        AssignmentRequest(
            interview_id="itv-test-001",
            position="Backend Engineer",
            jd_text="Junior backend: Python required",
            cv_markdown="# Dev\nPython basics",
            assignment_brief=DIRECTIVE_DSA,
            level="junior",
        )
    )
    assert assignment.type.value == "coding"
    assert assignment.coding.mode.value == "dsa"  # type: ignore[union-attr]
    assert assignment.coding.ai_assistant_enabled is False  # type: ignore[union-attr]
    assert meta["path"] == "deterministic-dsa"


@pytest.mark.asyncio
async def test_run_assignment_project_fallback():
    assignment, meta = await run_assignment_agent(
        AssignmentRequest(
            interview_id="itv-test-003",
            position="Frontend Engineer",
            jd_text="React, JavaScript, CSS",
            cv_markdown="# FE\n3 years React",
            coding_mode="project",
            level="mid",
            assignment_brief=DIRECTIVE_PROJECT,
        )
    )
    assert assignment.type.value == "coding"
    assert assignment.coding.mode.value == "project"  # type: ignore[union-attr]
    assert assignment.coding.ai_assistant_enabled is True  # type: ignore[union-attr]
    assert "App.js" in assignment.coding.starter_files  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_run_assignment_cognitive_nontech():
    assignment, meta = await run_assignment_agent(
        AssignmentRequest(
            interview_id="itv-test-002",
            position="Marketing Manager",
            jd_text="Drive campaigns and brand growth",
            cv_markdown="# Marketer\n5 years B2B campaigns",
            track="nontech",
            level="mid",
        )
    )
    assert assignment.type.value == "cognitive"
    assert len(assignment.cognitive.questions) == 10  # type: ignore[union-attr]