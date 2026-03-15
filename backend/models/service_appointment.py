"""
Service Appointment Model
Manages scheduled service appointments
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import enum

from . import Base


class AppointmentStatus(str, enum.Enum):
    """Appointment status"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SCHEDULED = "SCHEDULED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class AppointmentType(str, enum.Enum):
    """Type of appointment"""
    SCHEDULED_MAINTENANCE = "SCHEDULED_MAINTENANCE"
    PREDICTIVE_MAINTENANCE = "PREDICTIVE_MAINTENANCE"
    EMERGENCY_REPAIR = "EMERGENCY_REPAIR"
    RECALL = "RECALL"
    INSPECTION = "INSPECTION"
    WARRANTY_WORK = "WARRANTY_WORK"
    CUSTOMER_REQUEST = "CUSTOMER_REQUEST"


class UrgencyLevel(str, enum.Enum):
    """Urgency level"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ServiceAppointment(Base):
    """
    Service Appointment Entity
    Represents a scheduled service appointment
    """
    __tablename__ = "service_appointments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference
    appointment_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False, index=True)
    service_center_id = Column(Integer, ForeignKey("service_centers.id"), nullable=False, index=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)
    cost_estimate_id = Column(Integer, ForeignKey("cost_estimates.id"), nullable=True)
    
    # Status
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.PENDING)
    appointment_type = Column(SQLEnum(AppointmentType), nullable=False)
    urgency = Column(SQLEnum(UrgencyLevel), default=UrgencyLevel.MEDIUM)
    
    # Scheduling
    requested_date = Column(DateTime, nullable=True)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    scheduled_end_time = Column(DateTime, nullable=True)
    estimated_duration_minutes = Column(Integer, default=60)
    
    # Actual Times
    check_in_time = Column(DateTime, nullable=True)
    service_start_time = Column(DateTime, nullable=True)
    service_end_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    # Service Details
    service_description = Column(Text, nullable=True)
    services_requested = Column(JSON, nullable=True)  # List of service codes
    services_performed = Column(JSON, nullable=True)  # List of completed services
    
    # AI Scheduling Info
    ai_scheduled = Column(Boolean, default=False)
    scheduling_reason = Column(Text, nullable=True)
    alternative_slots = Column(JSON, nullable=True)  # Other available time slots
    
    # Customer Info
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(100), nullable=True)
    customer_notes = Column(Text, nullable=True)
    
    # Drop-off Details
    drop_off_mode = Column(String(20), default="DRIVE_IN")  # DRIVE_IN, PICKUP, TOW
    pickup_required = Column(Boolean, default=False)
    pickup_address = Column(Text, nullable=True)
    loaner_vehicle_required = Column(Boolean, default=False)
    loaner_vehicle_id = Column(String(50), nullable=True)
    
    # Technician Assignment
    assigned_technician_id = Column(String(50), nullable=True)
    assigned_technician_name = Column(String(100), nullable=True)
    assigned_bay = Column(String(20), nullable=True)
    
    # Work Order
    work_order_number = Column(String(50), nullable=True)
    work_order_created = Column(DateTime, nullable=True)
    
    # Parts
    parts_ordered = Column(Boolean, default=False)
    parts_received = Column(Boolean, default=False)
    parts_eta = Column(DateTime, nullable=True)
    
    # Completion
    completion_notes = Column(Text, nullable=True)
    quality_check_passed = Column(Boolean, nullable=True)
    quality_check_notes = Column(Text, nullable=True)
    
    # Notifications
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime, nullable=True)
    confirmation_sent = Column(Boolean, default=False)
    confirmation_sent_at = Column(DateTime, nullable=True)
    
    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String(100), nullable=True)
    
    # Rescheduling
    reschedule_count = Column(Integer, default=0)
    original_date = Column(DateTime, nullable=True)
    rescheduled_from_id = Column(Integer, nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="appointments")
    service_center = relationship("ServiceCenter", back_populates="appointments")
    feedback = relationship("Feedback", back_populates="appointment", uselist=False)
    
    __table_args__ = (
        Index("idx_appointment_date", "scheduled_date"),
        Index("idx_appointment_status", "status"),
        Index("idx_appointment_center_date", "service_center_id", "scheduled_date"),
        Index("idx_appointment_vehicle", "vehicle_id"),
    )
    
    def __repr__(self):
        return f"<ServiceAppointment(id={self.appointment_id}, status={self.status}, date={self.scheduled_date})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "appointment_id": self.appointment_id,
            "vehicle_id": self.vehicle_uuid,
            "service_center_id": self.service_center_id,
            "status": self.status.value if self.status else None,
            "appointment_type": self.appointment_type.value if self.appointment_type else None,
            "urgency": self.urgency.value if self.urgency else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "service_description": self.service_description,
            "ai_scheduled": self.ai_scheduled,
            "customer_name": self.customer_name,
            "assigned_technician": self.assigned_technician_name,
            "work_order_number": self.work_order_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def can_cancel(self) -> bool:
        """Check if appointment can be cancelled"""
        if self.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            return False
        if self.status == AppointmentStatus.IN_PROGRESS:
            return False
        return True
    
    def can_reschedule(self) -> bool:
        """Check if appointment can be rescheduled"""
        if self.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.IN_PROGRESS]:
            return False
        if self.reschedule_count >= 3:
            return False
        return True
    
    def get_duration(self) -> Optional[timedelta]:
        """Get actual service duration"""
        if self.service_start_time and self.service_end_time:
            return self.service_end_time - self.service_start_time
        return None