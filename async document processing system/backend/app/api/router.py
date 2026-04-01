from fastapi import APIRouter

from app.api.routes.projects import router as projects_router
from app.api.routes.runs import router as runs_router


api_router = APIRouter()
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(runs_router, prefix="/runs", tags=["runs"])
