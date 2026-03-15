"""
Routes Module
API endpoint definitions for all resources
"""

from fastapi import APIRouter

from .vehicle_routes import router as vehicle_router
from .telemetry_routes import router as telemetry_router
from .diagnosis_routes import router as diagnosis_router
from .cost_routes import router as cost_router
from .appointment_routes import router as appointment_router
from .service_center_routes import router as service_center_router
from .behavior_routes import router as behavior_router
from .feedback_routes import router as feedback_router
from .security_routes import router as security_router
from .agent_routes import router as agent_router
from .dashboard_routes import router as dashboard_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(
    vehicle_router,
    prefix="/vehicles",
    tags=["Vehicles"],
)
api_router.include_router(
    telemetry_router,
    prefix="/telemetry",
    tags=["Telemetry"],
)
api_router.include_router(
    diagnosis_router,
    prefix="/diagnoses",
    tags=["Diagnoses"],
)
api_router.include_router(
    cost_router,
    prefix="/cost-estimates",
    tags=["Cost Estimates"],
)
api_router.include_router(
    appointment_router,
    prefix="/appointments",
    tags=["Appointments"],
)
api_router.include_router(
    service_center_router,
    prefix="/service-centers",
    tags=["Service Centers"],
)
api_router.include_router(
    behavior_router,
    prefix="/driver-behavior",
    tags=["Driver Behavior"],
)
api_router.include_router(
    feedback_router,
    prefix="/feedback",
    tags=["Feedback & RCA/CAPA"],
)
api_router.include_router(
    security_router,
    prefix="/security",
    tags=["Security & UEBA"],
)
api_router.include_router(
    agent_router,
    prefix="/agents",
    tags=["AI Agents"],
)
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

__all__ = ["api_router"]