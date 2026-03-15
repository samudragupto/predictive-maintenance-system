"""
Vehicle Routes
API endpoints for vehicle management
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends
from typing import Optional
import logging

from backend.services.vehicle_service import VehicleService, get_vehicle_service
from backend.models.schemas import (
    VehicleCreate, VehicleUpdate, VehicleResponse,
    VehicleListResponse, BaseResponse,
)
from backend.utils.exceptions import (
    NotFoundException, ValidationException, ConflictException,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> VehicleService:
    return get_vehicle_service()


@router.post("", response_model=None, status_code=201)
async def create_vehicle(
    data: VehicleCreate,
    service: VehicleService = Depends(get_service),
):
    """Create a new vehicle"""
    try:
        result = await service.create_vehicle(data)
        return {"success": True, "data": result, "message": "Vehicle created successfully"}
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=None)
async def list_vehicles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    fleet_id: Optional[str] = Query(None, description="Filter by fleet ID"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    service: VehicleService = Depends(get_service),
):
    """Get paginated list of vehicles"""
    try:
        result = await service.get_vehicles(
            page=page,
            page_size=page_size,
            status=status,
            health_status=health_status,
            fleet_id=fleet_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return result
    except Exception as e:
        logger.error(f"Error listing vehicles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fleet-overview", response_model=None)
async def get_fleet_overview(
    fleet_id: Optional[str] = Query(None, description="Fleet ID"),
    service: VehicleService = Depends(get_service),
):
    """Get fleet overview statistics"""
    try:
        result = await service.get_fleet_overview(fleet_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting fleet overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/needing-service", response_model=None)
async def get_vehicles_needing_service(
    limit: int = Query(20, ge=1, le=100),
    service: VehicleService = Depends(get_service),
):
    """Get vehicles that need service"""
    try:
        result = await service.get_vehicles_needing_service(limit)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting vehicles needing service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vehicle_id}", response_model=None)
async def get_vehicle(
    vehicle_id: str = Path(..., description="Vehicle ID or VIN"),
    service: VehicleService = Depends(get_service),
):
    """Get a vehicle by ID or VIN"""
    try:
        result = await service.get_vehicle(vehicle_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{vehicle_id}", response_model=None)
async def update_vehicle(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    data: VehicleUpdate = None,
    service: VehicleService = Depends(get_service),
):
    """Update a vehicle"""
    try:
        result = await service.update_vehicle(vehicle_id, data)
        return {"success": True, "data": result, "message": "Vehicle updated successfully"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error updating vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vehicle_id}", response_model=None)
async def delete_vehicle(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    service: VehicleService = Depends(get_service),
):
    """Delete a vehicle (soft delete)"""
    try:
        result = await service.delete_vehicle(vehicle_id)
        return result
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error deleting vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{vehicle_id}/health-score", response_model=None)
async def update_health_score(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    health_score: float = Query(..., ge=0, le=100, description="Health score"),
    service: VehicleService = Depends(get_service),
):
    """Update vehicle health score"""
    try:
        result = await service.update_health_score(vehicle_id, health_score)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error updating health score: {e}")
        raise HTTPException(status_code=500, detail=str(e))