"""
Cost Estimate Routes
API endpoints for cost estimation
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, List
import logging

from backend.services.cost_service import CostEstimationService, get_cost_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> CostEstimationService:
    return get_cost_service()


@router.post("", response_model=None, status_code=201)
async def create_cost_estimate(
    vehicle_id: str = Query(..., description="Vehicle ID"),
    diagnosis_id: Optional[str] = Query(None, description="Diagnosis ID"),
    services_requested: Optional[List[str]] = Body(None),
    service: CostEstimationService = Depends(get_service),
):
    """Create a cost estimate for a vehicle"""
    try:
        result = await service.create_estimate(
            vehicle_id=vehicle_id,
            diagnosis_id=diagnosis_id,
            services_requested=services_requested,
        )
        return {"success": True, "data": result, "message": "Cost estimate created"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating cost estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{estimate_id}", response_model=None)
async def get_cost_estimate(
    estimate_id: str = Path(..., description="Estimate ID"),
    service: CostEstimationService = Depends(get_service),
):
    """Get a cost estimate by ID"""
    try:
        result = await service.get_estimate(estimate_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting cost estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicle/{vehicle_id}", response_model=None)
async def get_vehicle_estimates(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    service: CostEstimationService = Depends(get_service),
):
    """Get cost estimates for a vehicle"""
    try:
        result = await service.get_vehicle_estimates(vehicle_id, page, page_size)
        return result
    except Exception as e:
        logger.error(f"Error getting vehicle estimates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{estimate_id}/approve", response_model=None)
async def approve_estimate(
    estimate_id: str = Path(..., description="Estimate ID"),
    approved_by: str = Query("admin", description="Approver name"),
    service: CostEstimationService = Depends(get_service),
):
    """Approve a cost estimate"""
    try:
        result = await service.approve_estimate(estimate_id, approved_by)
        return {"success": True, "data": result, "message": "Estimate approved"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error approving estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))