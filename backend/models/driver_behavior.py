"""
Driver Behavior Model
Tracks and analyzes driver behavior patterns
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List
import enum

from . import Base


class BehaviorRating(str, enum.Enum):
    """Driver behavior rating"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    CRITICAL = "CRITICAL"


class EventSeverity(str, enum.Enum):
    """Driving event severity"""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(str, enum.Enum):
    """Type of driving event"""
    HARSH_ACCELERATION = "HARSH_ACCELERATION"
    HARSH_BRAKING = "HARSH_BRAKING"
    HARSH_CORNERING = "HARSH_CORNERING"
    SPEEDING = "SPEEDING"
    IDLE_EXCESSIVE = "IDLE_EXCESSIVE"
    RAPID_LANE_CHANGE = "RAPID_LANE_CHANGE"
    TAILGATING = "TAILGATING"
    DISTRACTED_DRIVING = "DISTRACTED_DRIVING"
    FATIGUE_DETECTED = "FATIGUE_DETECTED"
    SEATBELT_VIOLATION = "SEATBELT_VIOLATION"
    PHONE_USAGE = "PHONE_USAGE"
    FUEL_INEFFICIENT = "FUEL_INEFFICIENT"


class DriverBehavior(Base):
    """
    Driver Behavior Entity
    Aggregated driver behavior analysis
    """
    __tablename__ = "driver_behaviors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # References
    behavior_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False)
    driver_id = Column(String(50), nullable=True, index=True)
    driver_name = Column(String(100), nullable=True)
    
    # Analysis Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20), default="DAILY")  # DAILY, WEEKLY, MONTHLY
    
    # Overall Score
    overall_score = Column(Float, nullable=False)  # 0-100
    rating = Column(SQLEnum(BehaviorRating), nullable=False)
    
    # Category Scores
    acceleration_score = Column(Float, nullable=True)
    braking_score = Column(Float, nullable=True)
    cornering_score = Column(Float, nullable=True)
    speed_score = Column(Float, nullable=True)
    fuel_efficiency_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    
    # Driving Statistics
    total_distance_km = Column(Float, default=0.0)
    total_driving_time_minutes = Column(Integer, default=0)
    total_idle_time_minutes = Column(Integer, default=0)
    average_speed_kmh = Column(Float, nullable=True)
    max_speed_kmh = Column(Float, nullable=True)
    
    # Fuel Analysis
    fuel_consumed_liters = Column(Float, nullable=True)
    fuel_efficiency_kmpl = Column(Float, nullable=True)
    eco_driving_percentage = Column(Float, nullable=True)
    
    # Event Counts
    harsh_acceleration_count = Column(Integer, default=0)
    harsh_braking_count = Column(Integer, default=0)
    harsh_cornering_count = Column(Integer, default=0)
    speeding_count = Column(Integer, default=0)
    total_events_count = Column(Integer, default=0)
    
    # Risk Assessment
    risk_score = Column(Float, nullable=True)  # 0-100 (higher = more risky)
    accident_probability = Column(Float, nullable=True)
    
    # Comparisons
    score_vs_fleet_average = Column(Float, nullable=True)  # +/- percentage
    rank_in_fleet = Column(Integer, nullable=True)
    fleet_size = Column(Integer, nullable=True)
    
    # Recommendations
    recommendations = Column(JSON, nullable=True)  # List of improvement suggestions
    focus_areas = Column(JSON, nullable=True)  # Areas needing attention
    
    # AI Analysis
    ai_insights = Column(Text, nullable=True)
    behavior_pattern = Column(String(50), nullable=True)  # AGGRESSIVE, CAUTIOUS, NORMAL
    
    # Trends
    score_trend = Column(String(20), nullable=True)  # IMPROVING, STABLE, DECLINING
    previous_score = Column(Float, nullable=True)
    score_change = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="driver_behaviors")
    events = relationship("DrivingEvent", back_populates="behavior_record", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_behavior_vehicle_period", "vehicle_id", "period_start"),
        Index("idx_behavior_driver", "driver_id"),
        Index("idx_behavior_rating", "rating"),
    )
    
    def __repr__(self):
        return f"<DriverBehavior(id={self.behavior_id}, score={self.overall_score}, rating={self.rating})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "behavior_id": self.behavior_id,
            "vehicle_id": self.vehicle_uuid,
            "driver_id": self.driver_id,
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
                "type": self.period_type,
            },
            "overall_score": self.overall_score,
            "rating": self.rating.value if self.rating else None,
            "category_scores": {
                "acceleration": self.acceleration_score,
                "braking": self.braking_score,
                "cornering": self.cornering_score,
                "speed": self.speed_score,
                "fuel_efficiency": self.fuel_efficiency_score,
                "safety": self.safety_score,
            },
            "statistics": {
                "distance_km": self.total_distance_km,
                "driving_minutes": self.total_driving_time_minutes,
                "average_speed": self.average_speed_kmh,
            },
            "events": {
                "total": self.total_events_count,
                "harsh_acceleration": self.harsh_acceleration_count,
                "harsh_braking": self.harsh_braking_count,
                "speeding": self.speeding_count,
            },
            "risk_score": self.risk_score,
            "recommendations": self.recommendations,
            "trend": self.score_trend,
        }


class DrivingEvent(Base):
    """
    Driving Event
    Individual driving events/incidents
    """
    __tablename__ = "driving_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # References
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    behavior_id = Column(Integer, ForeignKey("driver_behaviors.id", ondelete="CASCADE"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    vehicle_uuid = Column(String(50), nullable=False, index=True)
    driver_id = Column(String(50), nullable=True)
    
    # Event Details
    event_type = Column(SQLEnum(EventType), nullable=False)
    severity = Column(SQLEnum(EventSeverity), default=EventSeverity.LOW)
    
    # Timestamp & Location
    event_timestamp = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(200), nullable=True)
    road_type = Column(String(50), nullable=True)  # HIGHWAY, URBAN, RURAL
    
    # Measurements
    speed_at_event = Column(Float, nullable=True)
    speed_limit = Column(Float, nullable=True)
    speed_over_limit = Column(Float, nullable=True)
    acceleration_g = Column(Float, nullable=True)
    deceleration_g = Column(Float, nullable=True)
    lateral_g = Column(Float, nullable=True)
    heading_change_degrees = Column(Float, nullable=True)
    
    # Duration
    duration_seconds = Column(Float, nullable=True)
    
    # Context
    weather_condition = Column(String(50), nullable=True)
    road_condition = Column(String(50), nullable=True)
    traffic_density = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    time_of_day = Column(String(20), nullable=True)  # MORNING, AFTERNOON, EVENING, NIGHT
    
    # Description
    description = Column(Text, nullable=True)
    
    # Video/Evidence
    video_clip_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    
    # Acknowledgement
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    
    # Follow-up
    coaching_required = Column(Boolean, default=False)
    coaching_completed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    behavior_record = relationship("DriverBehavior", back_populates="events")
    
    __table_args__ = (
        Index("idx_event_vehicle_time", "vehicle_uuid", "event_timestamp"),
        Index("idx_event_type", "event_type"),
        Index("idx_event_severity", "severity"),
    )
    
    def __repr__(self):
        return f"<DrivingEvent(id={self.event_id}, type={self.event_type}, severity={self.severity})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "vehicle_id": self.vehicle_uuid,
            "event_type": self.event_type.value if self.event_type else None,
            "severity": self.severity.value if self.severity else None,
            "timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "name": self.location_name,
            },
            "speed": self.speed_at_event,
            "speed_limit": self.speed_limit,
            "description": self.description,
            "acknowledged": self.acknowledged,
        }