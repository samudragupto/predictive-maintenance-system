"""
Dashboard Routes
API endpoints for the OEM Operations Dashboard
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import logging

from backend.services.vehicle_service import VehicleService, get_vehicle_service
from backend.services.diagnosis_service import DiagnosisService, get_diagnosis_service
from backend.services.appointment_service import AppointmentService, get_appointment_service
from backend.services.feedback_service import FeedbackService, get_feedback_service
from backend.services.security_service import SecurityService, get_security_service
from backend.services.telemetry_service import TelemetryService, get_telemetry_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=None)
async def get_dashboard():
    """Get complete dashboard data"""
    try:
        vehicle_service = get_vehicle_service()
        diagnosis_service = get_diagnosis_service()
        appointment_service = get_appointment_service()
        feedback_service = get_feedback_service()
        security_service = get_security_service()
        telemetry_service = get_telemetry_service()

        # Gather all dashboard data
        fleet_overview = await vehicle_service.get_fleet_overview()
        recent_diagnoses = await diagnosis_service.get_recent_diagnoses(limit=10)
        upcoming_appointments = await appointment_service.get_upcoming_appointments(limit=10)
        vehicles_needing_service = await vehicle_service.get_vehicles_needing_service(limit=10)
        feedback_stats = await feedback_service.get_feedback_stats()
        alert_summary = await security_service.get_alert_summary()
        recent_alerts = await security_service.get_ueba_alerts(limit=5)
        real_time_data = await telemetry_service.get_all_vehicles_real_time()

        return {
            "success": True,
            "data": {
                "fleet_overview": fleet_overview,
                "recent_diagnoses": recent_diagnoses,
                "upcoming_appointments": upcoming_appointments,
                "vehicles_needing_service": vehicles_needing_service,
                "feedback_stats": feedback_stats,
                "alert_summary": alert_summary,
                "recent_alerts": recent_alerts,
                "real_time_vehicles": real_time_data.get("vehicle_count", 0),
            },
        }
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fleet", response_model=None)
async def get_fleet_dashboard(
    fleet_id: Optional[str] = Query(None, description="Fleet ID"),
):
    """Get fleet-specific dashboard data"""
    try:
        vehicle_service = get_vehicle_service()
        overview = await vehicle_service.get_fleet_overview(fleet_id)
        needing_service = await vehicle_service.get_vehicles_needing_service(limit=20)

        return {
            "success": True,
            "data": {
                "overview": overview,
                "vehicles_needing_service": needing_service,
            },
        }
    except Exception as e:
        logger.error(f"Error getting fleet dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicle/{vehicle_id}", response_model=None)
async def get_vehicle_dashboard(
    vehicle_id: str,
):
    """Get vehicle-specific dashboard data"""
    try:
        vehicle_service = get_vehicle_service()
        diagnosis_service = get_diagnosis_service()
        telemetry_service = get_telemetry_service()

        vehicle = await vehicle_service.get_vehicle(vehicle_id)

        # Try to get telemetry and diagnosis, but don't fail if not available
        latest_telemetry = None
        risk_analysis = None
        recent_diagnoses = None

        try:
            latest_telemetry = await telemetry_service.get_latest_telemetry(vehicle_id)
        except Exception:
            pass

        try:
            risk_analysis = await telemetry_service.get_risk_analysis(vehicle_id)
        except Exception:
            pass

        try:
            diagnoses_result = await diagnosis_service.get_vehicle_diagnoses(
                vehicle_id, page=1, page_size=5
            )
            recent_diagnoses = diagnoses_result.get("data", [])
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "vehicle": vehicle,
                "latest_telemetry": latest_telemetry,
                "risk_analysis": risk_analysis,
                "recent_diagnoses": recent_diagnoses or [],
            },
        }
    except Exception as e:
        logger.error(f"Error getting vehicle dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs", response_model=None)
async def get_cost_dashboard():
    """Get cost overview dashboard"""
    try:
        feedback_service = get_feedback_service()
        stats = await feedback_service.get_feedback_stats()

        return {
            "success": True,
            "data": {
                "feedback_stats": stats,
                "cost_summary": {
                    "note": "Aggregate cost data available after service records are created",
                },
            },
        }
    except Exception as e:
        logger.error(f"Error getting cost dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security", response_model=None)
async def get_security_dashboard():
    """Get security overview dashboard"""
    try:
        security_service = get_security_service()

        alert_summary = await security_service.get_alert_summary()
        recent_alerts = await security_service.get_ueba_alerts(limit=20)
        recent_logs = await security_service.get_security_logs(page=1, page_size=20)

        return {
            "success": True,
            "data": {
                "alert_summary": alert_summary,
                "recent_alerts": recent_alerts,
                "recent_logs": recent_logs.get("data", []),
            },
        }
    except Exception as e:
        logger.error(f"Error getting security dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))