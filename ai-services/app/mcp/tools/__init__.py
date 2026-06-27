from app.mcp.tools.assignment import ASSIGNMENT_TOOLS
from app.mcp.tools.interview import INTERVIEW_TOOLS

ALL_TOOLS = {**INTERVIEW_TOOLS, **ASSIGNMENT_TOOLS}

__all__ = ["ALL_TOOLS", "INTERVIEW_TOOLS", "ASSIGNMENT_TOOLS"]