"""
Feedback & RCA/CAPA Routes
API endpoints for feedback management
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
import logging

from backend.services.feedback_service import FeedbackService, get_feedback_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> FeedbackService:
    return get_feedback_service()


@router.post("", response_model=None, status_code=201)
async def create_feedback(
    data: Dict[str, Any] = Body(...),
    service: FeedbackService = Depends(get_service),
):
    """Create a new feedback entry"""
    try:
        result = await service.create_feedback(data)
        return {"success": True, "data": result, "message": "Feedback submitted"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=None)
async def get_feedback_stats(
    service: FeedbackService = Depends(get_service),
):
    """Get feedback statistics"""
    try:
        result = await service.get_feedback_stats()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{feedback_id}", response_model=None)
async def get_feedback(
    feedback_id: str = Path(..., description="Feedback ID"),
    service: FeedbackService = Depends(get_service),
):
    """Get feedback by ID"""
    try:
        result = await service.get_feedback(feedback_id)
        return {"success": True, "data": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error getting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicle/{vehicle_id}", response_model=None)
async def get_vehicle_feedbacks(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    service: FeedbackService = Depends(get_service),
):
    """Get feedbacks for a vehicle"""
    try:
        result = await service.get_vehicle_feedbacks(vehicle_id, page, page_size)
        return result
    except Exception as e:
        logger.error(f"Error getting vehicle feedbacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rca", response_model=None, status_code=201)
async def create_rca(
    data: Dict[str, Any] = Body(...),
    service: FeedbackService = Depends(get_service),
):
    """Create an RCA report"""
    try:
        result = await service.create_rca(data)
        return {"success": True, "data": result, "message": "RCA report created"}
    except Exception as e:
        logger.error(f"Error creating RCA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rca/reports", response_model=None)
async def get_rca_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    service: FeedbackService = Depends(get_service),
):
    """Get RCA reports"""
    try:
        result = await service.get_rca_reports(status, limit)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting RCA reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rca/{rca_id}/capa", response_model=None, status_code=201)
async def create_capa(
    rca_id: str = Path(..., description="RCA Report ID"),
    data: Dict[str, Any] = Body(...),
    service: FeedbackService = Depends(get_service),
):
    """Create a CAPA action for an RCA report"""
    try:
        result = await service.create_capa(rca_id, data)
        return {"success": True, "data": result, "message": "CAPA created"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error creating CAPA: {e}")
        raise HTTPException(status_code=500, detail=str(e))