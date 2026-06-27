from fastapi import APIRouter

from app.api.planning_router import router as planning_router
from app.api.v1 import assignment, coding_assistant, inspector

api_router = APIRouter()
api_router.include_router(planning_router)
api_router.include_router(assignment.router)
api_router.include_router(coding_assistant.router)
api_router.include_router(inspector.router)