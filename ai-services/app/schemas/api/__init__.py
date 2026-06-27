from app.schemas.api.assignment import AssignmentGenerateRequest, AssignmentGenerateResponse
from app.schemas.api.coding_assistant import CodingAssistantRequest, CodingAssistantResponse
from app.schemas.api.inspector import InspectorEvaluateRequest, InspectorEvaluateResponse
from app.schemas.plan import InterviewPlan, PlanRequest, PlanResponse

# Legacy aliases
PlanningRequest = PlanRequest
PlanningResponse = PlanResponse

__all__ = [
    "PlanRequest",
    "PlanResponse",
    "InterviewPlan",
    "PlanningRequest",
    "PlanningResponse",
    "AssignmentGenerateRequest",
    "AssignmentGenerateResponse",
    "CodingAssistantRequest",
    "CodingAssistantResponse",
    "InspectorEvaluateRequest",
    "InspectorEvaluateResponse",
]