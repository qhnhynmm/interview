from app.schemas.plan import Domain, ProblemBankEntry

# Verified DSA reference problems — Assignment Agent copies test_cases verbatim for DSA mode.

PROBLEM_BANK: dict[tuple[Domain, str], list[ProblemBankEntry]] = {
    ("backend", "junior"): [
        ProblemBankEntry(
            title="Two Sum",
            difficulty="easy",
            statement=(
                "Given an integer array `nums` and an integer `target`, return indices of the "
                "two numbers such that they add up to `target`.\n\n"
                "You may assume each input has exactly one solution."
            ),
            function_name="two_sum",
            starter_code=(
                "def two_sum(nums: list[int], target: int) -> list[int]:\n"
                '    """Return indices of two numbers that add up to target."""\n'
                "    pass\n"
            ),
            test_cases=[
                {"label": "Basic", "inputs": [[2, 7, 11, 15], 9], "expected": [0, 1]},
                {"label": "Two elements", "inputs": [[3, 3], 6], "expected": [0, 1]},
            ],
        ),
    ],
    ("backend", "mid"): [
        ProblemBankEntry(
            title="Longest Substring Without Repeating Characters",
            difficulty="medium",
            statement=(
                "Given a string `s`, return the length of the longest substring "
                "without repeating characters."
            ),
            function_name="length_of_longest_substring",
            starter_code=(
                "def length_of_longest_substring(s: str) -> int:\n"
                '    """Return length of longest substring without repeats."""\n'
                "    pass\n"
            ),
            test_cases=[
                {"label": "Classic", "inputs": ["abcabcbb"], "expected": 3},
                {"label": "Single char repeat", "inputs": ["bbbbb"], "expected": 1},
                {"label": "Empty", "inputs": [""], "expected": 0},
            ],
        ),
    ],
    ("backend", "senior"): [
        ProblemBankEntry(
            title="LRU Cache",
            difficulty="hard",
            statement=(
                "Design a data structure for a Least Recently Used (LRU) cache.\n"
                "Implement `LRUCache` class with `get(key)` and `put(key, value)` in O(1)."
            ),
            function_name="LRUCache",
            starter_code=(
                "class LRUCache:\n"
                "    def __init__(self, capacity: int):\n"
                "        pass\n\n"
                "    def get(self, key: int) -> int:\n"
                "        pass\n\n"
                "    def put(self, key: int, value: int) -> None:\n"
                "        pass\n"
            ),
            test_cases=[
                {
                    "label": "Put and get",
                    "inputs": [[["put", 1, 1], ["put", 2, 2], ["get", 1], ["put", 3, 3], ["get", 2]]],
                    "expected": [None, None, 1, None, -1],
                },
            ],
        ),
    ],
    ("ai", "mid"): [
        ProblemBankEntry(
            title="Simple RAG Retrieval",
            difficulty="medium",
            statement=(
                "Implement `retrieve(query, documents, k)` returning top-k document indices "
                "by counting token overlap between query and each document (case-insensitive)."
            ),
            function_name="retrieve",
            starter_code=(
                "def retrieve(query: str, documents: list[str], k: int) -> list[int]:\n"
                '    """Return indices of top-k documents by token overlap."""\n'
                "    pass\n"
            ),
            test_cases=[
                {
                    "label": "Overlap ranking",
                    "inputs": ["payment api latency", ["payment service", "frontend css", "api gateway"], 2],
                    "expected": [0, 2],
                },
            ],
        ),
    ],
    ("frontend", "mid"): [
        ProblemBankEntry(
            title="Debounce Function",
            difficulty="medium",
            statement="Implement `debounce(fn, delay_ms)` that delays invoking `fn` until after `delay_ms` has elapsed since the last call.",
            function_name="debounce",
            starter_code=(
                "def debounce(fn, delay_ms):\n"
                '    """Return a debounced callable."""\n'
                "    pass\n"
            ),
            test_cases=[
                {"label": "Single trailing call", "inputs": [], "expected": "Only last rapid call fires after delay."},
            ],
        ),
    ],
    ("data", "mid"): [
        ProblemBankEntry(
            title="Sessionize Event Stream",
            difficulty="medium",
            statement="Group sorted events (each has `t` in minutes) into sessions when gap > 30 minutes.",
            function_name="sessionize",
            starter_code="def sessionize(events: list[dict]) -> int:\n    pass\n",
            test_cases=[
                {"label": "Two sessions", "inputs": [[{"t": 0}, {"t": 10}, {"t": 50}]], "expected": 2},
            ],
        ),
    ],
    ("devops", "mid"): [
        ProblemBankEntry(
            title="Resolve Config Overrides",
            difficulty="medium",
            statement=(
                "Given base config dict and ordered override layers, return merged config "
                "(later layers win on key conflicts)."
            ),
            function_name="resolve_config",
            starter_code=(
                "def resolve_config(base: dict, overrides: list[dict]) -> dict:\n"
                "    pass\n"
            ),
            test_cases=[
                {
                    "label": "Layered override",
                    "inputs": [{"timeout": 30}, [{"timeout": 60}, {"retries": 3}]],
                    "expected": {"timeout": 60, "retries": 3},
                },
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