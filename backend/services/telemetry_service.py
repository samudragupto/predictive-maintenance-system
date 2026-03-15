"""
Telemetry Service
Handles telemetry data management and processing
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import TelemetryData, TelemetrySnapshot, Vehicle, get_async_db_context
from backend.models.schemas import TelemetryCreate
from backend.telemetry.processor import TelemetryProcessor, RiskAnalyzer, get_processor
from backend.telemetry.simulator import TelemetrySimulator, get_simulator
from backend.telemetry.aggregator import TelemetryAggregator, get_aggregator
from backend.utils.helpers import timestamp_now
from backend.utils.validators import validate_telemetry_data
from backend.utils.exceptions import (
    NotFoundException,
    ValidationException,
    TelemetryException,
    DatabaseException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Service for managing telemetry data
    """

    def __init__(self):
        self.settings = get_settings()
        self.processor = get_processor()
        self.simulator = get_simulator()
        self.aggregator = get_aggregator()
        self.risk_analyzer = RiskAnalyzer()
        logger.info("TelemetryService initialized")

    async def ingest_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a single telemetry reading"""
        try:
            # 1. Validate data
            validation = validate_telemetry_data(data)
            if not validation.is_valid:
                raise ValidationException(
                    message="Invalid telemetry data",
                    details={"errors": [e.to_dict() for e in validation.errors]},
                )

            # 2. Try to send to Kafka (Real-Time Pipeline)
            try:
                from backend.telemetry.kafka_producer import get_kafka_producer
                producer = await get_kafka_producer()
                
                # If connected, send to Queue and return immediately (Fast!)
                if await producer.health_check():
                    await producer.send_telemetry(data)
                    
                    # Update local buffer for real-time dashboard view
                    self.aggregator.add_to_buffer(data.get("vehicle_id"), data)
                    
                    return {"success": True, "message": "Queued", "source": "kafka"}
            except Exception as e:
                logger.warning(f"Kafka unavailable, falling back to DB: {e}")

            # 3. Fallback: Save to Database directly (Slow path)
            result = await self.processor.process_telemetry(data)
            
            # Add to aggregator buffer
            self.aggregator.add_to_buffer(data.get("vehicle_id"), data)

            return result

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error ingesting telemetry: {e}")
            raise TelemetryException(
                message="Failed to ingest telemetry data",
                vehicle_id=data.get("vehicle_id"),
            )

    async def ingest_batch(
        self, readings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Ingest a batch of telemetry readings"""
        try:
            results = await self.processor.process_batch(readings)

            successful = sum(1 for r in results if r.get("success"))
            failed = len(results) - successful

            # Buffer all readings
            for reading in readings:
                vehicle_id = reading.get("vehicle_id")
                if vehicle_id:
                    self.aggregator.add_to_buffer(vehicle_id, reading)

            return {
                "success": failed == 0,
                "total": len(readings),
                "successful": successful,
                "failed": failed,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error ingesting batch: {e}")
            raise TelemetryException(
                message="Failed to ingest telemetry batch"
            )

    async def get_latest_telemetry(
        self, vehicle_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the latest telemetry reading for a vehicle"""
        try:
            # First check the in-memory buffer
            stats = self.aggregator.get_real_time_stats(vehicle_id)
            if stats:
                return {
                    "vehicle_id": vehicle_id,
                    "source": "real_time_buffer",
                    "data": stats,
                }

            # Fall back to database
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(TelemetryData)
                    .where(TelemetryData.vehicle_uuid == vehicle_id)
                    .order_by(desc(TelemetryData.timestamp))
                    .limit(1)
                )
                record = result.scalar_one_or_none()

                if not record:
                    return None

                return {
                    "vehicle_id": vehicle_id,
                    "source": "database",
                    "data": record.to_dict(),
                }

        except Exception as e:
            logger.error(
                f"Error getting latest telemetry for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get latest telemetry",
                operation="read",
                original_error=e,
            )

    async def get_telemetry_history(
        self,
        vehicle_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get telemetry history for a vehicle"""
        try:
            async with get_async_db_context() as session:
                since = timestamp_now() - timedelta(hours=hours)

                result = await session.execute(
                    select(TelemetryData)
                    .where(
                        and_(
                            TelemetryData.vehicle_uuid == vehicle_id,
                            TelemetryData.timestamp >= since,
                        )
                    )
                    .order_by(desc(TelemetryData.timestamp))
                    .limit(limit)
                )
                records = result.scalars().all()

                return {
                    "vehicle_id": vehicle_id,
                    "period_hours": hours,
                    "count": len(records),
                    "data": [r.to_dict() for r in records],
                }

        except Exception as e:
            logger.error(
                f"Error getting telemetry history for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get telemetry history",
                operation="read",
                original_error=e,
            )

    async def get_risk_analysis(
        self, vehicle_id: str
    ) -> Dict[str, Any]:
        """Get current risk analysis for a vehicle"""
        try:
            # Get latest telemetry from buffer
            stats = self.aggregator.get_real_time_stats(vehicle_id)

            if not stats:
                # Fall back to latest database record
                latest = await self.get_latest_telemetry(vehicle_id)
                if not latest:
                    raise NotFoundException(
                        resource="Telemetry data",
                        resource_id=vehicle_id,
                    )
                telemetry_data = latest.get("data", {})
            else:
                # Convert stats to telemetry format
                telemetry_data = {
                    "vehicle_id": vehicle_id,
                    "timestamp": stats.get("latest_timestamp", datetime.utcnow().isoformat()),
                    "engine_temperature_celsius": stats.get("engine_temperature", {}).get("latest"),
                    "battery_voltage": stats.get("battery_voltage", {}).get("latest"),
                    "oil_level_percent": stats.get("oil_level", {}).get("latest"),
                    "brake_pad_wear_front_percent": stats.get("brake_wear", {}).get("front"),
                    "brake_pad_wear_rear_percent": stats.get("brake_wear", {}).get("rear"),
                    "fuel_level_percent": stats.get("fuel_level", {}).get("latest"),
                    "tire_pressure_fl": None,
                    "tire_pressure_fr": None,
                    "tire_pressure_rl": None,
                    "tire_pressure_rr": None,
                }

            # Perform risk analysis
            assessment = self.risk_analyzer.analyze(telemetry_data)

            return {
                "vehicle_id": vehicle_id,
                "overall_risk_level": assessment.overall_risk_level,
                "health_score": assessment.health_score,
                "confidence_score": assessment.confidence_score,
                "requires_immediate_attention": assessment.requires_immediate_attention,
                "risk_indicators": [
                    {
                        "component": r.component,
                        "metric": r.metric_name,
                        "value": r.current_value,
                        "risk_level": r.risk_level,
                        "message": r.message,
                    }
                    for r in assessment.risk_indicators
                ],
                "recommended_actions": assessment.recommended_actions,
            }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting risk analysis for {vehicle_id}: {e}")
            raise TelemetryException(
                message="Failed to perform risk analysis",
                vehicle_id=vehicle_id,
            )

    async def simulate_telemetry(
        self, vehicle_count: int = 10
    ) -> Dict[str, Any]:
        """Start telemetry simulation"""
        try:
            profiles = self.simulator.create_default_fleet(vehicle_count)
            batch = await self.simulator.generate_batch()

            # Process the generated batch
            results = await self.ingest_batch(batch)

            return {
                "success": True,
                "vehicles_created": len(profiles),
                "telemetry_generated": len(batch),
                "processing_results": results,
            }

        except Exception as e:
            logger.error(f"Error simulating telemetry: {e}")
            raise TelemetryException(
                message="Failed to simulate telemetry"
            )

    async def generate_single_reading(
        self, vehicle_id: str
    ) -> Dict[str, Any]:
        """Generate a single simulated telemetry reading"""
        try:
            # Make sure vehicle is registered
            if vehicle_id not in self.simulator.vehicles:
                from backend.telemetry.simulator import VehicleSimulationProfile

                profile = VehicleSimulationProfile(
                    vehicle_id=vehicle_id,
                    vin="SIMULATED00000000",
                )
                self.simulator.register_vehicle(profile)

            telemetry = self.simulator.generate_telemetry(vehicle_id)
            if not telemetry:
                raise NotFoundException(
                    resource="Vehicle", resource_id=vehicle_id
                )

            # Process it
            result = await self.ingest_telemetry(telemetry)

            return {
                "telemetry": telemetry,
                "processing_result": result,
            }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error generating reading for {vehicle_id}: {e}")
            raise TelemetryException(
                message="Failed to generate telemetry reading",
                vehicle_id=vehicle_id,
            )

    async def get_snapshots(
        self,
        vehicle_id: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get telemetry snapshots for a vehicle"""
        try:
            return await self.aggregator.get_vehicle_history(
                vehicle_id, hours
            )
        except Exception as e:
            logger.error(f"Error getting snapshots for {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to get telemetry snapshots",
                operation="read",
                original_error=e,
            )

    async def get_all_vehicles_real_time(self) -> Dict[str, Any]:
        """Get real-time stats for all vehicles"""
        try:
            stats = self.aggregator.get_all_real_time_stats()
            return {
                "vehicle_count": len(stats),
                "vehicles": stats,
            }
        except Exception as e:
            logger.error(f"Error getting real-time stats: {e}")
            raise TelemetryException(
                message="Failed to get real-time statistics"
            )

    async def _update_vehicle_health(
        self, vehicle_id: str, health_score: float
    ) -> None:
        """Update vehicle health score in database"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
                )
                vehicle = result.scalar_one_or_none()

                if vehicle:
                    vehicle.update_health_status(health_score)
                    vehicle.last_telemetry_received = timestamp_now()
                    vehicle.updated_at = timestamp_now()
                    await session.commit()

        except Exception as e:
            logger.error(
                f"Error updating vehicle health for {vehicle_id}: {e}"
            )


# Singleton instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get or create telemetry service instance"""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service