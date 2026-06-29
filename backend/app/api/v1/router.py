from fastapi import APIRouter

from app.api.v1 import auth, interview_agent, interviews

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(interview_agent.router)
api_router.include_router(interviews.router)