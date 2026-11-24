from fastapi import APIRouter
from app.modules.users.controllers import auth_router
from app.modules.patients.controllers import patient_router
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(patient_router)