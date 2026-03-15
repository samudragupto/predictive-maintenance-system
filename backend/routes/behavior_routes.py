"""
Driver Behavior Routes
API endpoints for driver behavior analysis
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends
from typing import Optional
import logging

from backend.services.driver_behavior_service import DriverBehaviorService, get_driver_behavior_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> DriverBehaviorService:
    return get_driver_behavior_service()


@router.post("/analyze/{vehicle_id}", response_model=None, status_code=201)
async def analyze_behavior(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    period_type: str = Query("DAILY", description="Period type (DAILY/WEEKLY/MONTHLY)"),
    service: DriverBehaviorService = Depends(get_service),
):
    """Analyze driver behavior for a vehicle"""
    try:
        result = await service.analyze_behavior(vehicle_id, period_type)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error analyzing behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vehicle_id}", response_model=None)
async def get_behavior(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    period_type: str = Query("DAILY", description="Period type"),
    service: DriverBehaviorService = Depends(get_service),
):
    """Get latest behavior analysis for a vehicle"""
    try:
        result = await service.get_behavior(vehicle_id, period_type)
        if not result:
            raise HTTPException(status_code=404, detail="No behavior data found")
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vehicle_id}/history", response_model=None)
async def get_behavior_history(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    limit: int = Query(30, ge=1, le=100),
    service: DriverBehaviorService = Depends(get_service),
):
    """Get behavior history for a vehicle"""
    try:
        result = await service.get_behavior_history(vehicle_id, limit)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting behavior history: {e}")
        raise HTTPException(status_code=500, detail=str(e))