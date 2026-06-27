from fastapi import APIRouter

from app.api.assignment_router import router as assignment_router
from app.api.planning_router import router as planning_router
from app.api.v1 import coding_assistant, inspector

api_router = APIRouter()
api_router.include_router(planning_router)
api_router.include_router(assignment_router)
api_router.include_router(coding_assistant.router)
api_router.include_router(inspector.router)