"""
Service Center Routes
API endpoints for service center management
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
import logging

from backend.services.service_center_service import ServiceCenterService, get_service_center_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> ServiceCenterService:
    return get_service_center_service()


@router.post("", response_model=None, status_code=201)
async def create_service_center(
    data: Dict[str, Any] = Body(...),
    service: ServiceCenterService = Depends(get_service),
):
    """Create a new service center"""
    try:
        result = await service.create_service_center(data)
        return {"success": True, "data": result, "message": "Service center created"}
    except Exception as e:
        logger.error(f"Error creating service center: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=None)
async def list_service_centers(
    status: Optional[str] = Query(None, description="Filter by status"),
    city: Optional[str] = Query(None, description="Filter by city"),
    service: ServiceCenterService = Depends(get_service),
):
    """Get all service centers"""
    try:
        result = await service.get_all_centers(status=status, city=city)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error listing service centers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nearest", response_model=None)
async def find_nearest_centers(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    radius_km: float = Query(50.0, description="Search radius in km"),
    limit: int = Query(5, ge=1, le=20),
    service: ServiceCenterService = Depends(get_service),
):
    """Find nearest service centers"""
    try:
        result = await service.find_nearest_centers(
            latitude, longitude, radius_km, limit
        )
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error finding nearest centers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{center_id}", response_model=None)
async def get_service_center(
    center_id: str = Path(..., description="Service center ID"),
    service: ServiceCenterService = Depends(get_service),
):
    """Get a service center by ID"""
    try:
        result = await service.get_service_center(center_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting service center: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed", response_model=None, status_code=201)
async def seed_service_centers(
    service: ServiceCenterService = Depends(get_service),
):
    """Seed default service centers for development"""
    try:
        result = await service.seed_default_centers()
        return {"success": True, "data": result, "count": len(result), "message": "Service centers seeded"}
    except Exception as e:
        logger.error(f"Error seeding service centers: {e}")
        raise HTTPException(status_code=500, detail=str(e))