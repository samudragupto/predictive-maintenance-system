"""
Security & UEBA Routes
API endpoints for security monitoring
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
import logging

from backend.services.security_service import SecurityService, get_security_service
from backend.utils.exceptions import NotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> SecurityService:
    return get_security_service()


@router.get("/logs", response_model=None)
async def get_security_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: Optional[str] = Query(None, description="Log level filter"),
    actor_type: Optional[str] = Query(None, description="Actor type filter"),
    action_type: Optional[str] = Query(None, description="Action type filter"),
    service: SecurityService = Depends(get_service),
):
    """Get security logs"""
    try:
        result = await service.get_security_logs(
            page=page,
            page_size=page_size,
            level=level,
            actor_type=actor_type,
            action_type=action_type,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting security logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ueba/alerts", response_model=None)
async def get_ueba_alerts(
    status: Optional[str] = Query(None, description="Alert status filter"),
    severity: Optional[str] = Query(None, description="Severity filter"),
    limit: int = Query(20, ge=1, le=100),
    service: SecurityService = Depends(get_service),
):
    """Get UEBA alerts"""
    try:
        result = await service.get_ueba_alerts(status, severity, limit)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting UEBA alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ueba/alerts/summary", response_model=None)
async def get_alert_summary(
    service: SecurityService = Depends(get_service),
):
    """Get UEBA alert summary"""
    try:
        result = await service.get_alert_summary()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/ueba/alerts/{alert_id}", response_model=None)
async def update_ueba_alert(
    alert_id: str = Path(..., description="Alert ID"),
    data: Dict[str, Any] = Body(...),
    service: SecurityService = Depends(get_service),
):
    """Update a UEBA alert"""
    try:
        result = await service.update_ueba_alert(alert_id, data)
        return {"success": True, "data": result, "message": "Alert updated"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))