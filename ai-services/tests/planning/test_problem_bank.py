from app.skills.interview_planning.scripts.planning_tools import search_problem_bank


def test_problem_bank_fallback_chain():
    entry = search_problem_bank("backend", "senior")
    assert entry is not None
    assert entry.title
    assert entry.test_cases

    entry_fe = search_problem_bank("frontend", "junior")
    assert entry_fe is not None