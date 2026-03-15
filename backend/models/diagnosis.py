"""
Diagnosis Model
Stores AI-generated diagnoses and failure predictions
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any
import enum

from . import Base


class RiskLevel(str, enum.Enum):
    """Risk level classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DiagnosisStatus(str, enum.Enum):
    """Diagnosis processing status"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEWED = "REVIEWED"


class ComponentCategory(str, enum.Enum):
    """Vehicle component categories"""
    ENGINE = "ENGINE"
    TRANSMISSION = "TRANSMISSION"
    BRAKES = "BRAKES"
    BATTERY = "BATTERY"
    ELECTRICAL = "ELECTRICAL"
    COOLING_SYSTEM = "COOLING_SYSTEM"
    FUEL_SYSTEM = "FUEL_SYSTEM"
    EXHAUST = "EXHAUST"
    SUSPENSION = "SUSPENSION"
    STEERING = "STEERING"
    TIRES = "TIRES"
    BODY = "BODY"
    HVAC = "HVAC"
    OTHER = "OTHER"


class Diagnosis(Base):
    """
    Diagnosis Entity
    AI-generated diagnosis for a vehicle
    """
    __tablename__ = "diagnoses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference
    diagnosis_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False, index=True)
    
    # Trigger Information
    triggered_by = Column(String(50), nullable=False)  # "TELEMETRY", "SCHEDULE", "MANUAL", "DTC"
    trigger_telemetry_id = Column(Integer, ForeignKey("telemetry_data.id"), nullable=True)
    
    # Status
    status = Column(SQLEnum(DiagnosisStatus), default=DiagnosisStatus.PENDING)
    
    # Overall Assessment
    overall_risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    health_score = Column(Float, nullable=True)  # 0 to 100
    
    # AI Analysis
    summary = Column(Text, nullable=True)
    detailed_analysis = Column(Text, nullable=True)
    recommended_actions = Column(JSON, nullable=True)  # List of actions
    
    # Predicted Failures
    predicted_failures = Column(JSON, nullable=True)  # List of failure predictions
    failure_probability = Column(Float, nullable=True)  # 0.0 to 1.0
    estimated_days_to_failure = Column(Integer, nullable=True)
    
    # Affected Components
    affected_components = Column(JSON, nullable=True)  # List of component names
    primary_component = Column(SQLEnum(ComponentCategory), nullable=True)
    
    # Urgency
    requires_immediate_attention = Column(Boolean, default=False)
    service_recommended = Column(Boolean, default=False)
    service_urgency_days = Column(Integer, nullable=True)  # Days within which service is recommended
    
    # Model Information
    ml_model_used = Column(String(100), nullable=True)
    ml_model_version = Column(String(50), nullable=True)
    llm_model_used = Column(String(100), nullable=True)
    
    # Input Data
    input_telemetry_summary = Column(JSON, nullable=True)
    input_dtc_codes = Column(JSON, nullable=True)
    
    # Processing Time
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # Review
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    review_approved = Column(Boolean, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="diagnoses")
    details = relationship("DiagnosisDetail", back_populates="diagnosis", cascade="all, delete-orphan")
    failure_predictions = relationship("FailurePrediction", back_populates="diagnosis", cascade="all, delete-orphan")
    cost_estimate = relationship("CostEstimate", back_populates="diagnosis", uselist=False)
    
    __table_args__ = (
        Index("idx_diagnosis_vehicle", "vehicle_id"),
        Index("idx_diagnosis_risk", "overall_risk_level"),
        Index("idx_diagnosis_status", "status"),
        Index("idx_diagnosis_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<Diagnosis(id={self.diagnosis_id}, vehicle={self.vehicle_uuid}, risk={self.overall_risk_level})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "diagnosis_id": self.diagnosis_id,
            "vehicle_id": self.vehicle_uuid,
            "status": self.status.value if self.status else None,
            "overall_risk_level": self.overall_risk_level.value if self.overall_risk_level else None,
            "confidence_score": self.confidence_score,
            "health_score": self.health_score,
            "summary": self.summary,
            "recommended_actions": self.recommended_actions,
            "predicted_failures": self.predicted_failures,
            "failure_probability": self.failure_probability,
            "estimated_days_to_failure": self.estimated_days_to_failure,
            "affected_components": self.affected_components,
            "requires_immediate_attention": self.requires_immediate_attention,
            "service_recommended": self.service_recommended,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DiagnosisDetail(Base):
    """
    Diagnosis Detail
    Detailed breakdown per component
    """
    __tablename__ = "diagnosis_details"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    
    # Component
    component_category = Column(SQLEnum(ComponentCategory), nullable=False)
    component_name = Column(String(100), nullable=False)
    
    # Assessment
    status = Column(String(20), nullable=False)  # GOOD, WARNING, CRITICAL
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Values
    current_value = Column(Float, nullable=True)
    expected_range_min = Column(Float, nullable=True)
    expected_range_max = Column(Float, nullable=True)
    threshold_warning = Column(Float, nullable=True)
    threshold_critical = Column(Float, nullable=True)
    
    # Analysis
    issue_description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    impact_description = Column(Text, nullable=True)
    
    # Recommendations
    recommended_action = Column(Text, nullable=True)
    action_urgency = Column(String(20), nullable=True)  # IMMEDIATE, SOON, SCHEDULED
    estimated_repair_hours = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    diagnosis = relationship("Diagnosis", back_populates="details")
    
    def __repr__(self):
        return f"<DiagnosisDetail(component={self.component_name}, risk={self.risk_level})>"


class FailurePrediction(Base):
    """
    Failure Prediction
    Specific predicted failures with probabilities
    """
    __tablename__ = "failure_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    
    # Prediction Details
    prediction_id = Column(String(50), unique=True, nullable=False)
    component_category = Column(SQLEnum(ComponentCategory), nullable=False)
    component_name = Column(String(100), nullable=False)
    
    # Failure Details
    failure_type = Column(String(100), nullable=False)
    failure_description = Column(Text, nullable=True)
    
    # Probability & Timing
    probability = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    
    estimated_days_to_failure = Column(Integer, nullable=True)
    estimated_mileage_to_failure = Column(Float, nullable=True)
    earliest_failure_date = Column(DateTime, nullable=True)
    latest_failure_date = Column(DateTime, nullable=True)
    
    # Impact
    severity = Column(SQLEnum(RiskLevel), nullable=False)
    safety_impact = Column(Boolean, default=False)
    breakdown_risk = Column(Boolean, default=False)
    
    # Model Info
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    
    # Features Used
    contributing_factors = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    diagnosis = relationship("Diagnosis", back_populates="failure_predictions")
    
    def __repr__(self):
        return f"<FailurePrediction(component={self.component_name}, probability={self.probability})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "component": self.component_name,
            "failure_type": self.failure_type,
            "probability": self.probability,
            "estimated_days": self.estimated_days_to_failure,
            "severity": self.severity.value if self.severity else None,
            "safety_impact": self.safety_impact,
        }