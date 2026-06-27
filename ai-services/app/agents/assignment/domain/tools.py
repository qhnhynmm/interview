"""MAF tool surface for Assignment Agent."""

from app.skills.interview_planning.scripts.planning_tools import search_problem_bank_list

try:
    from agent_framework import tool

    @tool(approval_mode="never_require")
    def search_problem_bank(domain: str, level: str) -> list[dict]:
        """
        Search verified coding problems by domain and seniority level.
        domain: backend|frontend|data|devops|ai
        level: junior|mid|senior
        Returns problems with test_cases that must be copied verbatim for DSA mode.
        """
        return search_problem_bank_list(domain, level)

except ImportError:  # pragma: no cover
    def search_problem_bank(domain: str, level: str) -> list[dict]:  # type: ignore[misc]
        return search_problem_bank_list(domain, level)


__all__ = ["search_problem_bank"]