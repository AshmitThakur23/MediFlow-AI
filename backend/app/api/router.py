from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.encounters import router as encounters_router
from app.api.routes.clinical import router as clinical_router
from app.api.routes.patients import router as patients_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.api.routes.documents import router as documents_router
from app.api.routes.ai import router as ai_router
from app.api.routes.clinical_notes import router as clinical_notes_router
from app.core.config import settings


api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(patients_router)
api_router.include_router(appointments_router)
api_router.include_router(encounters_router)
api_router.include_router(clinical_router)
api_router.include_router(prescriptions_router)
api_router.include_router(documents_router)
api_router.include_router(ai_router)
api_router.include_router(clinical_notes_router)
