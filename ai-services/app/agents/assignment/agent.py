from app.agents.base import AgentBase
from app.schemas.api.assignment import AssignmentGenerateRequest
from app.schemas.api.common import CodingAssignment
from app.skills.problem_bank import pick_coding_problem


class AssignmentAgent(AgentBase):
    name = "assignment"

    async def run(self, request: AssignmentGenerateRequest) -> tuple[CodingAssignment, dict]:
        plan = request.plan or {}
        position = str(plan.get("position") or "Engineer")
        seniority = plan.get("seniority")
        skills = []
        if isinstance(plan.get("competencies"), list):
            skills = [str(c.get("name", "")) for c in plan["competencies"] if isinstance(c, dict)]

        assignment = pick_coding_problem(position=position, seniority=seniority, skills=skills)
        meta = {"agent": self.name, "mode": request.mode, "llm_used": False}
        return assignment, meta