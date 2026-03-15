"""
Vehicle Model
Represents vehicles in the fleet being monitored
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import enum

from . import Base


class VehicleStatus(str, enum.Enum):
    """Vehicle operational status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    IN_SERVICE = "IN_SERVICE"
    DECOMMISSIONED = "DECOMMISSIONED"
    PENDING_INSPECTION = "PENDING_INSPECTION"


class HealthStatus(str, enum.Enum):
    """Vehicle health status"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class FuelType(str, enum.Enum):
    """Vehicle fuel type"""
    PETROL = "PETROL"
    DIESEL = "DIESEL"
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"
    CNG = "CNG"
    LPG = "LPG"


class Vehicle(Base):
    """
    Vehicle Entity
    Stores all vehicle information and current status
    """
    __tablename__ = "vehicles"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vehicle Identification
    vehicle_id = Column(String(50), unique=True, nullable=False, index=True)
    vin = Column(String(17), unique=True, nullable=False, index=True)  # Vehicle Identification Number
    license_plate = Column(String(20), unique=True, nullable=True)
    
    # Vehicle Details
    make = Column(String(50), nullable=False)  # e.g., Toyota, Ford
    model = Column(String(50), nullable=False)  # e.g., Camry, F-150
    year = Column(Integer, nullable=False)
    variant = Column(String(50), nullable=True)  # e.g., XLE, Limited
    color = Column(String(30), nullable=True)
    fuel_type = Column(SQLEnum(FuelType), default=FuelType.PETROL)
    
    # Engine Details
    engine_type = Column(String(50), nullable=True)
    engine_capacity_cc = Column(Integer, nullable=True)
    transmission = Column(String(30), nullable=True)  # Automatic, Manual, CVT
    
    # Current Status
    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.ACTIVE, nullable=False)
    health_status = Column(SQLEnum(HealthStatus), default=HealthStatus.UNKNOWN, nullable=False)
    health_score = Column(Float, default=100.0)  # 0-100 score
    
    # Odometer & Usage
    current_mileage_km = Column(Float, default=0.0)
    average_daily_km = Column(Float, default=0.0)
    total_engine_hours = Column(Float, default=0.0)
    
    # Location (Last Known)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    
    # Ownership
    owner_id = Column(String(50), nullable=True, index=True)
    owner_name = Column(String(100), nullable=True)
    owner_contact = Column(String(50), nullable=True)
    fleet_id = Column(String(50), nullable=True, index=True)
    
    # Registration & Insurance
    registration_date = Column(DateTime, nullable=True)
    registration_expiry = Column(DateTime, nullable=True)
    insurance_provider = Column(String(100), nullable=True)
    insurance_expiry = Column(DateTime, nullable=True)
    
    # Last Service Info
    last_service_date = Column(DateTime, nullable=True)
    last_service_mileage = Column(Float, nullable=True)
    next_service_due_date = Column(DateTime, nullable=True)
    next_service_due_mileage = Column(Float, nullable=True)
    
    # Warranty
    warranty_start_date = Column(DateTime, nullable=True)
    warranty_end_date = Column(DateTime, nullable=True)
    warranty_mileage_limit = Column(Float, nullable=True)
    is_under_warranty = Column(Boolean, default=True)
    
    # IoT Device Info
    telemetry_device_id = Column(String(50), nullable=True)
    telemetry_device_status = Column(String(20), default="ACTIVE")
    last_telemetry_received = Column(DateTime, nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)  # Additional custom fields
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # ["fleet-a", "priority-high"]
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Soft Delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    telemetry_records = relationship("TelemetryData", back_populates="vehicle", lazy="dynamic")
    telemetry_snapshots = relationship("TelemetrySnapshot", back_populates="vehicle", lazy="dynamic")
    diagnoses = relationship("Diagnosis", back_populates="vehicle", lazy="dynamic")
    cost_estimates = relationship("CostEstimate", back_populates="vehicle", lazy="dynamic")
    appointments = relationship("ServiceAppointment", back_populates="vehicle", lazy="dynamic")
    driver_behaviors = relationship("DriverBehavior", back_populates="vehicle", lazy="dynamic")
    feedbacks = relationship("Feedback", back_populates="vehicle", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("idx_vehicle_status", "status"),
        Index("idx_vehicle_health", "health_status"),
        Index("idx_vehicle_fleet", "fleet_id"),
        Index("idx_vehicle_owner", "owner_id"),
        Index("idx_vehicle_make_model", "make", "model"),
    )
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, vehicle_id={self.vehicle_id}, {self.make} {self.model} {self.year})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "vin": self.vin,
            "license_plate": self.license_plate,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "fuel_type": self.fuel_type.value if self.fuel_type else None,
            "status": self.status.value if self.status else None,
            "health_status": self.health_status.value if self.health_status else None,
            "health_score": self.health_score,
            "current_mileage_km": self.current_mileage_km,
            "last_service_date": self.last_service_date.isoformat() if self.last_service_date else None,
            "next_service_due_date": self.next_service_due_date.isoformat() if self.next_service_due_date else None,
            "is_under_warranty": self.is_under_warranty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def update_health_status(self, score: float):
        """Update health status based on score"""
        self.health_score = score
        if score >= 80:
            self.health_status = HealthStatus.HEALTHY
        elif score >= 50:
            self.health_status = HealthStatus.WARNING
        else:
            self.health_status = HealthStatus.CRITICAL
    
    def is_service_due(self) -> bool:
        """Check if service is due"""
        if self.next_service_due_date and self.next_service_due_date <= datetime.now():
            return True
        if self.next_service_due_mileage and self.current_mileage_km >= self.next_service_due_mileage:
            return True
        return False