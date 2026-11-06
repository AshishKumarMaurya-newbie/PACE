from fastapi import APIRouter

from app.api.v1 import activities, analytics, auth, dashboard, export, health, imports, records, strength, training

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(activities.router)
api_router.include_router(dashboard.router)
api_router.include_router(analytics.router)
api_router.include_router(strength.router)
api_router.include_router(training.router)
api_router.include_router(health.router)
api_router.include_router(records.router)
api_router.include_router(export.router)
api_router.include_router(imports.router)