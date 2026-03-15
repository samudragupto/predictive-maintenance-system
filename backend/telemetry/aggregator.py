"""
Telemetry Aggregator
Aggregates telemetry data for dashboards and reporting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.config.settings import get_settings
from backend.models import TelemetryData, TelemetrySnapshot, Vehicle
from backend.models import get_async_db_context

settings = get_settings()
logger = logging.getLogger(__name__)


class TelemetryAggregator:
    """
    Aggregates telemetry data for analysis and reporting
    Creates periodic snapshots of vehicle telemetry
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._is_running: bool = False
        self._aggregation_task: Optional[asyncio.Task] = None
        
        # In-memory buffer for real-time aggregation
        self._buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._buffer_max_size: int = 1000
        
        logger.info("TelemetryAggregator initialized")
    
    def add_to_buffer(self, vehicle_id: str, telemetry: Dict[str, Any]) -> None:
        """Add telemetry to in-memory buffer"""
        self._buffer[vehicle_id].append(telemetry)
        
        # Limit buffer size
        if len(self._buffer[vehicle_id]) > self._buffer_max_size:
            self._buffer[vehicle_id] = self._buffer[vehicle_id][-self._buffer_max_size:]
    
    def get_real_time_stats(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time statistics from buffer"""
        readings = self._buffer.get(vehicle_id, [])
        if not readings:
            return None
        
        return self._calculate_stats(readings)
    
    def get_all_real_time_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get real-time statistics for all vehicles"""
        return {
            vehicle_id: self._calculate_stats(readings)
            for vehicle_id, readings in self._buffer.items()
            if readings
        }
    
    def _calculate_stats(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from readings"""
        if not readings:
            return {}
        
        # Extract numeric fields
        engine_temps = [r.get("engine_temperature_celsius") for r in readings if r.get("engine_temperature_celsius")]
        battery_voltages = [r.get("battery_voltage") for r in readings if r.get("battery_voltage")]
        speeds = [r.get("speed_kmh") for r in readings if r.get("speed_kmh") is not None]
        oil_levels = [r.get("oil_level_percent") for r in readings if r.get("oil_level_percent")]
        fuel_levels = [r.get("fuel_level_percent") for r in readings if r.get("fuel_level_percent")]
        
        stats = {
            "reading_count": len(readings),
            "latest_timestamp": readings[-1].get("timestamp") if readings else None,
        }
        
        # Engine temperature stats
        if engine_temps:
            stats["engine_temperature"] = {
                "latest": engine_temps[-1],
                "avg": round(statistics.mean(engine_temps), 2),
                "max": round(max(engine_temps), 2),
                "min": round(min(engine_temps), 2),
            }
        
        # Battery voltage stats
        if battery_voltages:
            stats["battery_voltage"] = {
                "latest": battery_voltages[-1],
                "avg": round(statistics.mean(battery_voltages), 2),
                "min": round(min(battery_voltages), 2),
            }
        
        # Speed stats
        if speeds:
            stats["speed"] = {
                "latest": speeds[-1],
                "avg": round(statistics.mean(speeds), 2),
                "max": round(max(speeds), 2),
            }
        
        # Oil level
        if oil_levels:
            stats["oil_level"] = {
                "latest": oil_levels[-1],
                "trend": "decreasing" if len(oil_levels) > 1 and oil_levels[-1] < oil_levels[0] else "stable",
            }
        
        # Fuel level
        if fuel_levels:
            stats["fuel_level"] = {
                "latest": fuel_levels[-1],
            }
        
        # Get latest brake wear
        latest = readings[-1]
        stats["brake_wear"] = {
            "front": latest.get("brake_pad_wear_front_percent"),
            "rear": latest.get("brake_pad_wear_rear_percent"),
        }
        
        # Location
        if latest.get("latitude") and latest.get("longitude"):
            stats["location"] = {
                "latitude": latest.get("latitude"),
                "longitude": latest.get("longitude"),
            }
        
        # DTCs
        dtcs = latest.get("dtc_codes")
        if dtcs:
            stats["active_dtcs"] = dtcs
        
        return stats
    
    async def create_snapshot(
        self,
        vehicle_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[Dict[str, Any]]:
        """Create a snapshot for a specific period"""
        try:
            async with get_async_db_context() as session:
                # Query telemetry data for the period
                query = select(TelemetryData).where(
                    and_(
                        TelemetryData.vehicle_uuid == vehicle_id,
                        TelemetryData.timestamp >= period_start,
                        TelemetryData.timestamp <= period_end,
                    )
                ).order_by(TelemetryData.timestamp)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                if not records:
                    logger.debug(f"No telemetry data for {vehicle_id} in period")
                    return None
                
                # Calculate aggregates
                snapshot_data = self._aggregate_records(records)
                snapshot_data["vehicle_uuid"] = vehicle_id
                snapshot_data["period_start"] = period_start
                snapshot_data["period_end"] = period_end
                snapshot_data["snapshot_time"] = datetime.utcnow()
                snapshot_data["reading_count"] = len(records)
                
                # Create snapshot record
                snapshot = TelemetrySnapshot(
                    vehicle_uuid=vehicle_id,
                    snapshot_time=snapshot_data["snapshot_time"],
                    period_start=period_start,
                    period_end=period_end,
                    avg_engine_temp=snapshot_data.get("avg_engine_temp"),
                    max_engine_temp=snapshot_data.get("max_engine_temp"),
                    avg_battery_voltage=snapshot_data.get("avg_battery_voltage"),
                    min_battery_voltage=snapshot_data.get("min_battery_voltage"),
                    avg_speed=snapshot_data.get("avg_speed"),
                    max_speed=snapshot_data.get("max_speed"),
                    total_distance_km=snapshot_data.get("total_distance_km"),
                    avg_fuel_consumption=snapshot_data.get("avg_fuel_consumption"),
                    latest_oil_level=snapshot_data.get("latest_oil_level"),
                    latest_brake_wear_front=snapshot_data.get("latest_brake_wear_front"),
                    latest_brake_wear_rear=snapshot_data.get("latest_brake_wear_rear"),
                    latest_fuel_level=snapshot_data.get("latest_fuel_level"),
                    tire_pressure_fl=snapshot_data.get("tire_pressure_fl"),
                    tire_pressure_fr=snapshot_data.get("tire_pressure_fr"),
                    tire_pressure_rl=snapshot_data.get("tire_pressure_rl"),
                    tire_pressure_rr=snapshot_data.get("tire_pressure_rr"),
                    health_score=snapshot_data.get("health_score"),
                    risk_level=snapshot_data.get("risk_level"),
                    active_dtcs=snapshot_data.get("active_dtcs"),
                    reading_count=len(records),
                    anomaly_count=snapshot_data.get("anomaly_count", 0),
                )
                
                session.add(snapshot)
                await session.commit()
                
                logger.info(f"Created snapshot for {vehicle_id}: {period_start} to {period_end}")
                return snapshot_data
                
        except Exception as e:
            logger.error(f"Error creating snapshot for {vehicle_id}: {e}")
            return None
    
    def _aggregate_records(self, records: List[TelemetryData]) -> Dict[str, Any]:
        """Aggregate telemetry records"""
        if not records:
            return {}
        
        # Extract values
        engine_temps = [r.engine_temperature_celsius for r in records if r.engine_temperature_celsius]
        battery_voltages = [r.battery_voltage for r in records if r.battery_voltage]
        speeds = [r.speed_kmh for r in records if r.speed_kmh is not None]
        fuel_consumptions = [r.fuel_consumption_rate for r in records if r.fuel_consumption_rate]
        
        latest = records[-1]
        
        aggregated = {}
        
        # Engine temperature
        if engine_temps:
            aggregated["avg_engine_temp"] = round(statistics.mean(engine_temps), 2)
            aggregated["max_engine_temp"] = round(max(engine_temps), 2)
        
        # Battery voltage
        if battery_voltages:
            aggregated["avg_battery_voltage"] = round(statistics.mean(battery_voltages), 2)
            aggregated["min_battery_voltage"] = round(min(battery_voltages), 2)
        
        # Speed
        if speeds:
            aggregated["avg_speed"] = round(statistics.mean(speeds), 2)
            aggregated["max_speed"] = round(max(speeds), 2)
        
        # Distance
        odometers = [r.odometer_km for r in records if r.odometer_km]
        if len(odometers) >= 2:
            aggregated["total_distance_km"] = round(odometers[-1] - odometers[0], 2)
        
        # Fuel consumption
        if fuel_consumptions:
            aggregated["avg_fuel_consumption"] = round(statistics.mean(fuel_consumptions), 2)
        
        # Latest values
        aggregated["latest_oil_level"] = latest.oil_level_percent
        aggregated["latest_brake_wear_front"] = latest.brake_pad_wear_front_percent
        aggregated["latest_brake_wear_rear"] = latest.brake_pad_wear_rear_percent
        aggregated["latest_fuel_level"] = latest.fuel_level_percent
        
        # Tire pressures
        aggregated["tire_pressure_fl"] = latest.tire_pressure_fl
        aggregated["tire_pressure_fr"] = latest.tire_pressure_fr
        aggregated["tire_pressure_rl"] = latest.tire_pressure_rl
        aggregated["tire_pressure_rr"] = latest.tire_pressure_rr
        
        # DTCs
        all_dtcs = set()
        for r in records:
            if r.dtc_codes:
                all_dtcs.update(r.dtc_codes)
        if all_dtcs:
            aggregated["active_dtcs"] = list(all_dtcs)
        
        # Calculate health score (simplified)
        health_score = 100.0
        deductions = 0
        
        if aggregated.get("max_engine_temp", 0) > 100:
            deductions += 15
        if aggregated.get("min_battery_voltage", 13) < 12:
            deductions += 10
        if aggregated.get("latest_oil_level", 100) < 30:
            deductions += 20
        if aggregated.get("latest_brake_wear_front", 0) > 80:
            deductions += 25
        if aggregated.get("active_dtcs"):
            deductions += len(aggregated["active_dtcs"]) * 5
        
        aggregated["health_score"] = max(0, health_score - deductions)
        
        # Risk level
        if aggregated["health_score"] >= 80:
            aggregated["risk_level"] = "LOW"
        elif aggregated["health_score"] >= 60:
            aggregated["risk_level"] = "MEDIUM"
        elif aggregated["health_score"] >= 40:
            aggregated["risk_level"] = "HIGH"
        else:
            aggregated["risk_level"] = "CRITICAL"
        
        return aggregated
    
    async def run_periodic_aggregation(self, interval_minutes: int = 5) -> None:
        """Run periodic aggregation for all vehicles"""
        self._is_running = True
        logger.info(f"Starting periodic aggregation every {interval_minutes} minutes")
        
        while self._is_running:
            try:
                await self._aggregate_all_vehicles(interval_minutes)
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic aggregation error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
        
        logger.info("Periodic aggregation stopped")
    
    async def _aggregate_all_vehicles(self, interval_minutes: int) -> None:
        """Aggregate data for all active vehicles"""
        try:
            async with get_async_db_context() as session:
                # Get all active vehicle IDs
                query = select(Vehicle.vehicle_id).where(Vehicle.status == "ACTIVE")
                result = await session.execute(query)
                vehicle_ids = [row[0] for row in result.fetchall()]
                
                period_end = datetime.utcnow()
                period_start = period_end - timedelta(minutes=interval_minutes)
                
                for vehicle_id in vehicle_ids:
                    await self.create_snapshot(vehicle_id, period_start, period_end)
                
                logger.info(f"Aggregated data for {len(vehicle_ids)} vehicles")
                
        except Exception as e:
            logger.error(f"Error aggregating all vehicles: {e}")
    
    def stop_aggregation(self) -> None:
        """Stop periodic aggregation"""
        self._is_running = False
        if self._aggregation_task:
            self._aggregation_task.cancel()
    
    async def get_vehicle_history(
        self,
        vehicle_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical snapshots for a vehicle"""
        try:
            async with get_async_db_context() as session:
                since = datetime.utcnow() - timedelta(hours=hours)
                
                query = select(TelemetrySnapshot).where(
                    and_(
                        TelemetrySnapshot.vehicle_uuid == vehicle_id,
                        TelemetrySnapshot.snapshot_time >= since,
                    )
                ).order_by(TelemetrySnapshot.snapshot_time)
                
                result = await session.execute(query)
                snapshots = result.scalars().all()
                
                return [
                    {
                        "snapshot_time": s.snapshot_time.isoformat(),
                        "health_score": s.health_score,
                        "risk_level": s.risk_level,
                        "avg_engine_temp": s.avg_engine_temp,
                        "avg_battery_voltage": s.avg_battery_voltage,
                        "avg_speed": s.avg_speed,
                        "total_distance_km": s.total_distance_km,
                    }
                    for s in snapshots
                ]
                
        except Exception as e:
            logger.error(f"Error getting vehicle history: {e}")
            return []
    
    def clear_buffer(self, vehicle_id: Optional[str] = None) -> None:
        """Clear the in-memory buffer"""
        if vehicle_id:
            self._buffer.pop(vehicle_id, None)
        else:
            self._buffer.clear()


# Singleton instance
_aggregator_instance: Optional[TelemetryAggregator] = None


def get_aggregator() -> TelemetryAggregator:
    """Get or create aggregator instance"""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = TelemetryAggregator()
    return _aggregator_instance