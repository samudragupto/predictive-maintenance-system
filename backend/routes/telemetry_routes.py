"""
Telemetry Routes
API endpoints for telemetry data management
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, List, Dict, Any
import logging

from backend.services.telemetry_service import TelemetryService, get_telemetry_service

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> TelemetryService:
    return get_telemetry_service()


@router.post("/ingest", response_model=None, status_code=201)
async def ingest_telemetry(
    data: Dict[str, Any] = Body(...),
    service: TelemetryService = Depends(get_service),
):
    """Ingest a single telemetry reading"""
    try:
        result = await service.ingest_telemetry(data)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error ingesting telemetry: {e}")
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/ingest/batch", response_model=None, status_code=201)
async def ingest_telemetry_batch(
    readings: List[Dict[str, Any]] = Body(...),
    service: TelemetryService = Depends(get_service),
):
    """Ingest a batch of telemetry readings"""
    try:
        result = await service.ingest_batch(readings)
        return result
    except Exception as e:
        logger.error(f"Error ingesting batch: {e}")
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/latest/{vehicle_id}", response_model=None)
async def get_latest_telemetry(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    service: TelemetryService = Depends(get_service),
):
    """Get latest telemetry for a vehicle"""
    try:
        result = await service.get_latest_telemetry(vehicle_id)
        if not result:
            raise HTTPException(status_code=404, detail="No telemetry data found")
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{vehicle_id}", response_model=None)
async def get_telemetry_history(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    hours: int = Query(24, ge=1, le=720, description="Hours of history"),
    limit: int = Query(100, ge=1, le=1000, description="Max records"),
    service: TelemetryService = Depends(get_service),
):
    """Get telemetry history for a vehicle"""
    try:
        result = await service.get_telemetry_history(vehicle_id, hours, limit)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting telemetry history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-analysis/{vehicle_id}", response_model=None)
async def get_risk_analysis(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    service: TelemetryService = Depends(get_service),
):
    """Get current risk analysis for a vehicle"""
    try:
        result = await service.get_risk_analysis(vehicle_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting risk analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{vehicle_id}", response_model=None)
async def get_telemetry_snapshots(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    hours: int = Query(24, ge=1, le=720, description="Hours of history"),
    service: TelemetryService = Depends(get_service),
):
    """Get telemetry snapshots for a vehicle"""
    try:
        result = await service.get_snapshots(vehicle_id, hours)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/real-time", response_model=None)
async def get_all_real_time(
    service: TelemetryService = Depends(get_service),
):
    """Get real-time telemetry stats for all vehicles"""
    try:
        result = await service.get_all_vehicles_real_time()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting real-time stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate", response_model=None, status_code=201)
async def simulate_telemetry(
    vehicle_count: int = Query(10, ge=1, le=100, description="Number of vehicles"),
    service: TelemetryService = Depends(get_service),
):
    """Start telemetry simulation"""
    try:
        result = await service.simulate_telemetry(vehicle_count)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error simulating telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate/{vehicle_id}", response_model=None, status_code=201)
async def simulate_single_reading(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    service: TelemetryService = Depends(get_service),
):
    """Generate a single simulated reading for a vehicle"""
    try:
        result = await service.generate_single_reading(vehicle_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error generating reading: {e}")
        raise HTTPException(status_code=500, detail=str(e))