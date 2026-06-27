from app.schemas.plan import Difficulty, Domain, ProblemBankEntry

# Verified reference problems — difficulty calibration only (Assignment Agent generates real tasks).

PROBLEM_BANK: dict[tuple[Domain, str], list[ProblemBankEntry]] = {
    ("backend", "junior"): [
        ProblemBankEntry(
            title="Valid Parentheses",
            difficulty="easy",
            statement="Given a string of brackets, return True if valid.",
            function_name="is_valid",
            starter_code="def is_valid(s: str) -> bool:\n    pass\n",
            test_cases=[
                {"input": {"s": "()"}, "expected": True},
                {"input": {"s": "([)]"}, "expected": False},
            ],
        ),
    ],
    ("backend", "mid"): [
        ProblemBankEntry(
            title="LRU Cache",
            difficulty="medium",
            statement="Design an LRU cache with get and put in O(1).",
            function_name="LRUCache",
            starter_code="class LRUCache:\n    def __init__(self, capacity: int):\n        pass\n",
            test_cases=[
                {"input": {"ops": [["put", 1, 1], ["get", 1]]}, "expected": [None, 1]},
            ],
        ),
        ProblemBankEntry(
            title="Rate Limiter API",
            difficulty="medium",
            statement="Implement a sliding-window rate limiter for HTTP handlers.",
            function_name="allow_request",
            starter_code="def allow_request(user_id: str, ts: int) -> bool:\n    pass\n",
            test_cases=[
                {"input": {"user_id": "u1", "ts": 1}, "expected": True},
            ],
        ),
    ],
    ("backend", "senior"): [
        ProblemBankEntry(
            title="Consistent Hash Ring",
            difficulty="hard",
            statement="Implement add/remove node and key lookup on a consistent hash ring.",
            function_name="lookup",
            starter_code="class HashRing:\n    def __init__(self, nodes):\n        pass\n",
            test_cases=[
                {"input": {"key": "user:42"}, "expected": "node-a"},
            ],
        ),
    ],
    ("frontend", "mid"): [
        ProblemBankEntry(
            title="Debounced Search",
            difficulty="medium",
            statement="Implement a debounced async search hook with cancellation.",
            function_name="useDebouncedSearch",
            starter_code="export function useDebouncedSearch(fn, delayMs) {\n  // TODO\n}\n",
            test_cases=[
                {"input": {"queries": ["a", "ab"]}, "expected": 1},
            ],
        ),
    ],
    ("data", "mid"): [
        ProblemBankEntry(
            title="Sessionize Events",
            difficulty="medium",
            statement="Group sorted events into sessions when gap > 30 minutes.",
            function_name="sessionize",
            starter_code="def sessionize(events):\n    pass\n",
            test_cases=[
                {"input": {"events": [{"t": 0}, {"t": 10}, {"t": 50}]}, "expected": 2},
            ],
        ),
    ],
    ("devops", "senior"): [
        ProblemBankEntry(
            title="Rolling Deploy Safety",
            difficulty="hard",
            statement="Simulate a rolling deploy with max unavailable and health checks.",
            function_name="simulate_rollout",
            starter_code="def simulate_rollout(instances, batch):\n    pass\n",
            test_cases=[
                {"input": {"instances": 6, "batch": 2}, "expected": 3},
            ],
        ),
    ],
    ("ai", "mid"): [
        ProblemBankEntry(
            title="RAG Chunk Ranker",
            difficulty="medium",
            statement="Re-rank retrieved chunks by BM25 + embedding cosine hybrid score.",
            function_name="rerank",
            starter_code="def rerank(query, chunks, k=5):\n    pass\n",
            test_cases=[
                {"input": {"query": "latency", "chunks": ["cache", "latency SLO"]}, "expected": 2},
            ],
        ),
    ],
}

_LEVEL_ALIASES = {
    "junior": "junior",
    "mid": "mid",
    "middle": "mid",
    "senior": "senior",
    "manager": "senior",
}