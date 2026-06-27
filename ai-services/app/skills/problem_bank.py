import hashlib

from app.schemas.api.common import CodingAssignment

_PROBLEMS: list[dict] = [
    {
        "title": "Two Sum",
        "difficulty": "medium",
        "mode": "dsa",
        "description": (
            "Given an array of integers `nums` and an integer `target`, return indices of the "
            "two numbers such that they add up to `target`.\n\n"
            "You may assume each input has exactly one solution."
        ),
        "starter_code": (
            "# Write your solution here\n\n"
            "def two_sum(nums, target):\n"
            '    """Return indices of two numbers that add up to target."""\n'
            "    pass\n"
        ),
    },
    {
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "mode": "dsa",
        "description": (
            "Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']',\n"
            "determine if the input string is valid."
        ),
        "starter_code": (
            "def is_valid(s: str) -> bool:\n"
            '    """Return True if brackets are balanced."""\n'
            "    pass\n"
        ),
    },
    {
        "title": "Reverse Linked List",
        "difficulty": "medium",
        "mode": "dsa",
        "description": "Reverse a singly linked list and return the new head.",
        "starter_code": (
            "class ListNode:\n"
            "    def __init__(self, val=0, next=None):\n"
            "        self.val = val\n"
            "        self.next = next\n\n"
            "def reverse_list(head):\n"
            "    pass\n"
        ),
    },
]


def pick_coding_problem(*, position: str, seniority: str | None, skills: list[str]) -> CodingAssignment:
    seed = f"{position}|{seniority or ''}|{','.join(skills[:5])}"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(_PROBLEMS)
    row = _PROBLEMS[idx]
    return CodingAssignment(
        title=row["title"],
        difficulty=row["difficulty"],
        mode=row["mode"],
        ai_assistant_enabled=True,
        description=row["description"],
        starter_code=row["starter_code"],
    )