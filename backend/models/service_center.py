"""
Service Center Model
Authorized service center information
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, time
from typing import Dict, Any, List, Optional
import enum

from . import Base


class CenterStatus(str, enum.Enum):
    """Service center status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    CLOSED = "CLOSED"


class CenterType(str, enum.Enum):
    """Type of service center"""
    DEALERSHIP = "DEALERSHIP"
    AUTHORIZED_CENTER = "AUTHORIZED_CENTER"
    INDEPENDENT = "INDEPENDENT"
    MOBILE_SERVICE = "MOBILE_SERVICE"


class ServiceCenter(Base):
    """
    Service Center Entity
    Authorized service center information
    """
    __tablename__ = "service_centers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identification
    center_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    center_type = Column(SQLEnum(CenterType), default=CenterType.AUTHORIZED_CENTER)
    status = Column(SQLEnum(CenterStatus), default=CenterStatus.ACTIVE)
    
    # Location
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=False, default="USA")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    manager_name = Column(String(100), nullable=True)
    manager_phone = Column(String(20), nullable=True)
    
    # Operating Hours (stored as JSON for flexibility)
    operating_hours = Column(JSON, nullable=True)
    # Example: {"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {...}}
    timezone = Column(String(50), default="America/New_York")
    
    # Capacity
    total_bays = Column(Integer, default=5)
    available_bays = Column(Integer, default=5)
    max_daily_appointments = Column(Integer, default=20)
    average_service_time_minutes = Column(Integer, default=90)
    
    # Capabilities
    services_offered = Column(JSON, nullable=True)  # List of service codes
    vehicle_makes_supported = Column(JSON, nullable=True)  # ["Toyota", "Honda", ...]
    specializations = Column(JSON, nullable=True)  # ["EV", "Hybrid", "Performance"]
    certifications = Column(JSON, nullable=True)  # List of certifications
    
    # Equipment
    has_diagnostic_equipment = Column(Boolean, default=True)
    has_ev_charging = Column(Boolean, default=False)
    has_body_shop = Column(Boolean, default=False)
    has_tire_service = Column(Boolean, default=True)
    has_pickup_service = Column(Boolean, default=False)
    has_loaner_vehicles = Column(Boolean, default=False)
    loaner_vehicle_count = Column(Integer, default=0)
    
    # Ratings
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    nps_score = Column(Float, nullable=True)  # Net Promoter Score
    
    # Performance Metrics
    average_wait_time_minutes = Column(Integer, nullable=True)
    first_time_fix_rate = Column(Float, nullable=True)  # Percentage
    customer_satisfaction_score = Column(Float, nullable=True)
    
    # Pricing
    labor_rate_per_hour = Column(Float, default=75.0)
    diagnostic_fee = Column(Float, default=50.0)
    
    # Integration
    external_system_id = Column(String(100), nullable=True)
    api_endpoint = Column(String(200), nullable=True)
    
    # Flags
    is_premium = Column(Boolean, default=False)
    accepts_walk_ins = Column(Boolean, default=True)
    requires_appointment = Column(Boolean, default=False)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    appointments = relationship("ServiceAppointment", back_populates="service_center")
    capacities = relationship("ServiceCenterCapacity", back_populates="service_center", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_center_location", "latitude", "longitude"),
        Index("idx_center_city", "city"),
        Index("idx_center_status", "status"),
    )
    
    def __repr__(self):
        return f"<ServiceCenter(id={self.center_id}, name={self.name})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "center_id": self.center_id,
            "name": self.name,
            "center_type": self.center_type.value if self.center_type else None,
            "status": self.status.value if self.status else None,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "postal_code": self.postal_code,
                "country": self.country,
            },
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "contact": {
                "phone": self.phone,
                "email": self.email,
            },
            "operating_hours": self.operating_hours,
            "capacity": {
                "total_bays": self.total_bays,
                "available_bays": self.available_bays,
                "max_daily_appointments": self.max_daily_appointments,
            },
            "services_offered": self.services_offered,
            "rating": self.average_rating,
            "labor_rate": self.labor_rate_per_hour,
        }
    
    def is_open_on(self, day: str) -> bool:
        """Check if center is open on given day"""
        if not self.operating_hours:
            return False
        day_hours = self.operating_hours.get(day.lower())
        return day_hours is not None and day_hours.get("open") is not None
    
    def get_operating_hours_for_day(self, day: str) -> Optional[Dict[str, str]]:
        """Get operating hours for a specific day"""
        if not self.operating_hours:
            return None
        return self.operating_hours.get(day.lower())


class ServiceCenterCapacity(Base):
    """
    Service Center Capacity
    Daily capacity and slot availability
    """
    __tablename__ = "service_center_capacities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    service_center_id = Column(Integer, ForeignKey("service_centers.id", ondelete="CASCADE"), nullable=False)
    
    # Date
    date = Column(DateTime, nullable=False, index=True)
    
    # Capacity
    total_slots = Column(Integer, nullable=False)
    booked_slots = Column(Integer, default=0)
    available_slots = Column(Integer, nullable=False)
    
    # Time Slots (detailed availability)
    time_slots = Column(JSON, nullable=True)
    # Example: [{"time": "08:00", "available": true}, {"time": "09:00", "available": false}]
    
    # Staff
    technicians_available = Column(Integer, nullable=True)
    
    # Special
    is_holiday = Column(Boolean, default=False)
    is_reduced_hours = Column(Boolean, default=False)
    notes = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    service_center = relationship("ServiceCenter", back_populates="capacities")
    
    __table_args__ = (
        Index("idx_capacity_center_date", "service_center_id", "date"),
    )
    
    def __repr__(self):
        return f"<ServiceCenterCapacity(center={self.service_center_id}, date={self.date}, available={self.available_slots})>"