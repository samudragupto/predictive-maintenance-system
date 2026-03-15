"""
Telemetry Model
Stores real-time and historical vehicle telemetry data
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any
import enum

from . import Base


class TelemetrySource(str, enum.Enum):
    """Source of telemetry data"""
    OBD2 = "OBD2"
    CANBUS = "CANBUS"
    IOT_DEVICE = "IOT_DEVICE"
    MOBILE_APP = "MOBILE_APP"
    SIMULATION = "SIMULATION"


class TelemetryData(Base):
    """
    Raw Telemetry Data
    Individual telemetry readings from vehicles
    """
    __tablename__ = "telemetry_data"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False, index=True)  # For quick lookup
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Source
    source = Column(SQLEnum(TelemetrySource), default=TelemetrySource.IOT_DEVICE)
    device_id = Column(String(50), nullable=True)
    
    # Engine Metrics
    engine_temperature_celsius = Column(Float, nullable=True)
    engine_rpm = Column(Float, nullable=True)
    engine_load_percent = Column(Float, nullable=True)
    engine_oil_temperature = Column(Float, nullable=True)
    engine_coolant_temperature = Column(Float, nullable=True)
    
    # Fuel System
    fuel_level_percent = Column(Float, nullable=True)
    fuel_consumption_rate = Column(Float, nullable=True)  # L/100km
    fuel_pressure = Column(Float, nullable=True)
    
    # Oil System
    oil_level_percent = Column(Float, nullable=True)
    oil_pressure = Column(Float, nullable=True)
    oil_life_remaining = Column(Float, nullable=True)
    
    # Battery & Electrical
    battery_voltage = Column(Float, nullable=True)
    battery_current = Column(Float, nullable=True)
    battery_soc_percent = Column(Float, nullable=True)  # State of Charge (EV/Hybrid)
    battery_temperature = Column(Float, nullable=True)
    alternator_voltage = Column(Float, nullable=True)
    
    # Brakes
    brake_pad_wear_front_percent = Column(Float, nullable=True)
    brake_pad_wear_rear_percent = Column(Float, nullable=True)
    brake_fluid_level = Column(Float, nullable=True)
    abs_status = Column(Boolean, nullable=True)
    
    # Tires
    tire_pressure_fl = Column(Float, nullable=True)  # Front Left (PSI)
    tire_pressure_fr = Column(Float, nullable=True)  # Front Right
    tire_pressure_rl = Column(Float, nullable=True)  # Rear Left
    tire_pressure_rr = Column(Float, nullable=True)  # Rear Right
    tire_temperature_fl = Column(Float, nullable=True)
    tire_temperature_fr = Column(Float, nullable=True)
    tire_temperature_rl = Column(Float, nullable=True)
    tire_temperature_rr = Column(Float, nullable=True)
    
    # Transmission
    transmission_temperature = Column(Float, nullable=True)
    transmission_fluid_level = Column(Float, nullable=True)
    current_gear = Column(Integer, nullable=True)
    
    # Speed & Motion
    speed_kmh = Column(Float, nullable=True)
    acceleration_x = Column(Float, nullable=True)  # m/s²
    acceleration_y = Column(Float, nullable=True)
    acceleration_z = Column(Float, nullable=True)
    
    # Odometer
    odometer_km = Column(Float, nullable=True)
    trip_distance_km = Column(Float, nullable=True)
    
    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude_m = Column(Float, nullable=True)
    heading_degrees = Column(Float, nullable=True)
    gps_speed_kmh = Column(Float, nullable=True)
    
    # Environment
    ambient_temperature = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    
    # Exhaust & Emissions
    exhaust_gas_temperature = Column(Float, nullable=True)
    catalyst_temperature = Column(Float, nullable=True)
    oxygen_sensor_voltage = Column(Float, nullable=True)
    
    # Diagnostic Trouble Codes (DTCs)
    dtc_codes = Column(JSON, nullable=True)  # ["P0301", "P0420"]
    mil_status = Column(Boolean, nullable=True)  # Malfunction Indicator Light
    
    # Vibration & Noise
    vibration_level = Column(Float, nullable=True)
    noise_level_db = Column(Float, nullable=True)
    
    # Additional Sensors
    additional_data = Column(JSON, nullable=True)
    
    # Data Quality
    is_valid = Column(Boolean, default=True)
    quality_score = Column(Float, nullable=True)  # 0-100
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry_records")
    
    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_telemetry_vehicle_time", "vehicle_id", "timestamp"),
        Index("idx_telemetry_time", "timestamp"),
        Index("idx_telemetry_vehicle_uuid", "vehicle_uuid"),
    )
    
    def __repr__(self):
        return f"<TelemetryData(id={self.id}, vehicle={self.vehicle_uuid}, time={self.timestamp})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_uuid,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "engine_temperature": self.engine_temperature_celsius,
            "engine_rpm": self.engine_rpm,
            "battery_voltage": self.battery_voltage,
            "oil_level": self.oil_level_percent,
            "fuel_level": self.fuel_level_percent,
            "brake_wear_front": self.brake_pad_wear_front_percent,
            "brake_wear_rear": self.brake_pad_wear_rear_percent,
            "speed": self.speed_kmh,
            "odometer": self.odometer_km,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "dtc_codes": self.dtc_codes,
        }
    
    def get_risk_indicators(self) -> Dict[str, Any]:
        """Extract risk indicators from telemetry"""
        from backend.config.settings import get_settings
        settings = get_settings()
        
        risks = {}
        
        # Engine temperature check
        if self.engine_temperature_celsius:
            if self.engine_temperature_celsius >= settings.ENGINE_TEMP_CRITICAL:
                risks["engine_temp"] = {"level": "CRITICAL", "value": self.engine_temperature_celsius}
            elif self.engine_temperature_celsius >= settings.ENGINE_TEMP_WARNING:
                risks["engine_temp"] = {"level": "WARNING", "value": self.engine_temperature_celsius}
        
        # Battery voltage check
        if self.battery_voltage:
            if self.battery_voltage <= settings.BATTERY_VOLTAGE_CRITICAL:
                risks["battery"] = {"level": "CRITICAL", "value": self.battery_voltage}
            elif self.battery_voltage <= settings.BATTERY_VOLTAGE_LOW:
                risks["battery"] = {"level": "WARNING", "value": self.battery_voltage}
        
        # Brake wear check
        brake_wear = max(
            self.brake_pad_wear_front_percent or 0,
            self.brake_pad_wear_rear_percent or 0
        )
        if brake_wear:
            if brake_wear >= settings.BRAKE_WEAR_CRITICAL:
                risks["brakes"] = {"level": "CRITICAL", "value": brake_wear}
            elif brake_wear >= settings.BRAKE_WEAR_WARNING:
                risks["brakes"] = {"level": "WARNING", "value": brake_wear}
        
        # Oil level check
        if self.oil_level_percent:
            if self.oil_level_percent <= settings.OIL_LEVEL_CRITICAL:
                risks["oil"] = {"level": "CRITICAL", "value": self.oil_level_percent}
            elif self.oil_level_percent <= settings.OIL_LEVEL_LOW:
                risks["oil"] = {"level": "WARNING", "value": self.oil_level_percent}
        
        return risks


class TelemetrySnapshot(Base):
    """
    Telemetry Snapshot
    Aggregated/processed telemetry for dashboard display
    Stores periodic snapshots (e.g., every 5 minutes)
    """
    __tablename__ = "telemetry_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False, index=True)
    
    # Snapshot Time
    snapshot_time = Column(DateTime, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Aggregated Values (averages for the period)
    avg_engine_temp = Column(Float, nullable=True)
    max_engine_temp = Column(Float, nullable=True)
    avg_battery_voltage = Column(Float, nullable=True)
    min_battery_voltage = Column(Float, nullable=True)
    avg_speed = Column(Float, nullable=True)
    max_speed = Column(Float, nullable=True)
    total_distance_km = Column(Float, nullable=True)
    avg_fuel_consumption = Column(Float, nullable=True)
    
    # Latest Values
    latest_oil_level = Column(Float, nullable=True)
    latest_brake_wear_front = Column(Float, nullable=True)
    latest_brake_wear_rear = Column(Float, nullable=True)
    latest_fuel_level = Column(Float, nullable=True)
    
    # Tire Pressures (latest)
    tire_pressure_fl = Column(Float, nullable=True)
    tire_pressure_fr = Column(Float, nullable=True)
    tire_pressure_rl = Column(Float, nullable=True)
    tire_pressure_rr = Column(Float, nullable=True)
    
    # Health Metrics
    health_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    active_dtcs = Column(JSON, nullable=True)
    
    # Counts
    reading_count = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry_snapshots")
    
    __table_args__ = (
        Index("idx_snapshot_vehicle_time", "vehicle_id", "snapshot_time"),
    )
    
    def __repr__(self):
        return f"<TelemetrySnapshot(vehicle={self.vehicle_uuid}, time={self.snapshot_time})>"