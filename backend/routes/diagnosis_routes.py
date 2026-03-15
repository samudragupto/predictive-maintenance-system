"""
Diagnosis Routes
API endpoints for AI-powered diagnosis
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
import logging

from backend.services.diagnosis_service import DiagnosisService, get_diagnosis_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> DiagnosisService:
    return get_diagnosis_service()


@router.post("", response_model=None, status_code=201)
async def create_diagnosis(
    vehicle_id: str = Query(..., description="Vehicle ID"),
    triggered_by: str = Query("MANUAL", description="Trigger source"),
    telemetry_data: Optional[Dict[str, Any]] = Body(None),
    service: DiagnosisService = Depends(get_service),
):
    """Create a new diagnosis for a vehicle"""
    try:
        result = await service.create_diagnosis(
            vehicle_id=vehicle_id,
            triggered_by=triggered_by,
            telemetry_data=telemetry_data,
        )
        return {"success": True, "data": result, "message": "Diagnosis created successfully"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating diagnosis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=None)
async def get_recent_diagnoses(
    limit: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    service: DiagnosisService = Depends(get_service),
):
    """Get recent diagnoses across all vehicles"""
    try:
        result = await service.get_recent_diagnoses(limit, risk_level)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting recent diagnoses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{diagnosis_id}", response_model=None)
async def get_diagnosis(
    diagnosis_id: str = Path(..., description="Diagnosis ID"),
    service: DiagnosisService = Depends(get_service),
):
    """Get a diagnosis by ID"""
    try:
        result = await service.get_diagnosis(diagnosis_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting diagnosis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicle/{vehicle_id}", response_model=None)
async def get_vehicle_diagnoses(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    risk_level: Optional[str] = Query(None),
    service: DiagnosisService = Depends(get_service),
):
    """Get diagnoses for a specific vehicle"""
    try:
        result = await service.get_vehicle_diagnoses(
            vehicle_id, page, page_size, risk_level
        )
        return result
    except Exception as e:
        logger.error(f"Error getting vehicle diagnoses: {e}")
        raise HTTPException(status_code=500, detail=str(e))