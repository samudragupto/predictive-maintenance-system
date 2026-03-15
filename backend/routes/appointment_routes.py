"""
Appointment Routes
API endpoints for service appointment management
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from backend.services.appointment_service import AppointmentService, get_appointment_service
from backend.utils.exceptions import NotFoundException, ConflictException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> AppointmentService:
    return get_appointment_service()


@router.post("", response_model=None, status_code=201)
async def create_appointment(
    data: Dict[str, Any] = Body(...),
    service: AppointmentService = Depends(get_service),
):
    """Create a new appointment"""
    try:
        result = await service.create_appointment(data)
        return {"success": True, "data": result, "message": "Appointment created"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-schedule", response_model=None, status_code=201)
async def auto_schedule_appointment(
    vehicle_id: str = Query(..., description="Vehicle ID"),
    urgency: str = Query("MEDIUM", description="Urgency level"),
    diagnosis_id: Optional[str] = Query(None, description="Diagnosis ID"),
    service: AppointmentService = Depends(get_service),
):
    """Automatically schedule a service appointment"""
    try:
        result = await service.auto_schedule(
            vehicle_id=vehicle_id,
            diagnosis_id=diagnosis_id,
            urgency=urgency,
        )
        return {"success": True, "data": result, "message": "Appointment auto-scheduled"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error auto-scheduling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=None)
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    service: AppointmentService = Depends(get_service),
):
    """Get paginated appointments"""
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None

        result = await service.get_appointments(
            page=page,
            page_size=page_size,
            vehicle_id=vehicle_id,
            status=status,
            date_from=df,
            date_to=dt,
        )
        return result
    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming", response_model=None)
async def get_upcoming_appointments(
    limit: int = Query(10, ge=1, le=50),
    service: AppointmentService = Depends(get_service),
):
    """Get upcoming appointments"""
    try:
        result = await service.get_upcoming_appointments(limit)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting upcoming appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{appointment_id}", response_model=None)
async def get_appointment(
    appointment_id: str = Path(..., description="Appointment ID"),
    service: AppointmentService = Depends(get_service),
):
    """Get an appointment by ID"""
    try:
        result = await service.get_appointment(appointment_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{appointment_id}/status", response_model=None)
async def update_appointment_status(
    appointment_id: str = Path(..., description="Appointment ID"),
    status: str = Query(..., description="New status"),
    notes: Optional[str] = Query(None, description="Notes"),
    service: AppointmentService = Depends(get_service),
):
    """Update appointment status"""
    try:
        result = await service.update_appointment_status(
            appointment_id, status, notes
        )
        return {"success": True, "data": result, "message": f"Status updated to {status}"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))