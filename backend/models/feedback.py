"""
Feedback Model
Post-service feedback, RCA (Root Cause Analysis), and CAPA (Corrective and Preventive Actions)
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


class FeedbackType(str, enum.Enum):
    """Type of feedback"""
    SERVICE_FEEDBACK = "SERVICE_FEEDBACK"
    PREDICTION_ACCURACY = "PREDICTION_ACCURACY"
    COST_ACCURACY = "COST_ACCURACY"
    DIAGNOSIS_ACCURACY = "DIAGNOSIS_ACCURACY"
    GENERAL = "GENERAL"


class FeedbackSentiment(str, enum.Enum):
    """Feedback sentiment"""
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class RCAStatus(str, enum.Enum):
    """RCA status"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class CAPAStatus(str, enum.Enum):
    """CAPA status"""
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"


class CAPAType(str, enum.Enum):
    """Type of CAPA"""
    CORRECTIVE = "CORRECTIVE"
    PREVENTIVE = "PREVENTIVE"
    BOTH = "BOTH"


class Feedback(Base):
    """
    Feedback Entity
    Captures post-service feedback and outcomes
    """
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # References
    feedback_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False)
    appointment_id = Column(Integer, ForeignKey("service_appointments.id"), nullable=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)
    
    # Feedback Type
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    
    # Customer Ratings (1-5 scale)
    overall_rating = Column(Float, nullable=True)
    service_quality_rating = Column(Float, nullable=True)
    timeliness_rating = Column(Float, nullable=True)
    communication_rating = Column(Float, nullable=True)
    value_for_money_rating = Column(Float, nullable=True)
    
    # NPS
    nps_score = Column(Integer, nullable=True)  # 0-10
    would_recommend = Column(Boolean, nullable=True)
    
    # Comments
    customer_comments = Column(Text, nullable=True)
    sentiment = Column(SQLEnum(FeedbackSentiment), nullable=True)
    
    # Service Outcome
    issue_resolved = Column(Boolean, nullable=True)
    first_time_fix = Column(Boolean, nullable=True)
    repeat_visit_required = Column(Boolean, default=False)
    repeat_visit_reason = Column(Text, nullable=True)
    
    # Prediction Accuracy (for AI learning)
    prediction_was_accurate = Column(Boolean, nullable=True)
    actual_issue_description = Column(Text, nullable=True)
    actual_components_replaced = Column(JSON, nullable=True)
    predicted_vs_actual_match_percent = Column(Float, nullable=True)
    
    # Cost Accuracy
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    cost_variance = Column(Float, nullable=True)
    cost_variance_percent = Column(Float, nullable=True)
    
    # Time Accuracy
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    
    # Failure Prediction Outcome
    predicted_failure_occurred = Column(Boolean, nullable=True)
    failure_occurred_date = Column(DateTime, nullable=True)
    days_to_actual_failure = Column(Integer, nullable=True)
    
    # Service Center Response
    service_center_response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    responded_by = Column(String(100), nullable=True)
    
    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_completed = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)
    
    # RCA Trigger
    triggers_rca = Column(Boolean, default=False)
    rca_id = Column(Integer, ForeignKey("rca_reports.id"), nullable=True)
    
    # Source
    feedback_source = Column(String(50), nullable=True)  # APP, EMAIL, PHONE, SMS, IN_PERSON
    feedback_date = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="feedbacks")
    appointment = relationship("ServiceAppointment", back_populates="feedback")
    rca_report = relationship("RCAReport", back_populates="related_feedbacks", foreign_keys=[rca_id])
    
    __table_args__ = (
        Index("idx_feedback_vehicle", "vehicle_id"),
        Index("idx_feedback_date", "feedback_date"),
        Index("idx_feedback_type", "feedback_type"),
    )
    
    def __repr__(self):
        return f"<Feedback(id={self.feedback_id}, rating={self.overall_rating}, type={self.feedback_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "feedback_id": self.feedback_id,
            "vehicle_id": self.vehicle_uuid,
            "feedback_type": self.feedback_type.value if self.feedback_type else None,
            "ratings": {
                "overall": self.overall_rating,
                "service_quality": self.service_quality_rating,
                "timeliness": self.timeliness_rating,
                "communication": self.communication_rating,
                "value_for_money": self.value_for_money_rating,
            },
            "nps_score": self.nps_score,
            "sentiment": self.sentiment.value if self.sentiment else None,
            "customer_comments": self.customer_comments,
            "issue_resolved": self.issue_resolved,
            "first_time_fix": self.first_time_fix,
            "prediction_accuracy": {
                "was_accurate": self.prediction_was_accurate,
                "match_percent": self.predicted_vs_actual_match_percent,
            },
            "cost_accuracy": {
                "estimated": self.estimated_cost,
                "actual": self.actual_cost,
                "variance_percent": self.cost_variance_percent,
            },
            "feedback_date": self.feedback_date.isoformat() if self.feedback_date else None,
        }


class RCAReport(Base):
    """
    Root Cause Analysis Report
    Automated and manual RCA for issues
    """
    __tablename__ = "rca_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference
    rca_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Trigger
    trigger_type = Column(String(50), nullable=False)  # FEEDBACK, REPEAT_ISSUE, PREDICTION_MISS, MANUAL
    trigger_reference_id = Column(String(50), nullable=True)
    
    # Status
    status = Column(SQLEnum(RCAStatus), default=RCAStatus.OPEN)
    priority = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Problem Statement
    problem_title = Column(String(200), nullable=False)
    problem_description = Column(Text, nullable=False)
    
    # Impact
    vehicles_affected_count = Column(Integer, default=1)
    affected_vehicle_ids = Column(JSON, nullable=True)
    customer_impact = Column(Text, nullable=True)
    business_impact = Column(Text, nullable=True)
    
    # Timeline
    issue_first_detected = Column(DateTime, nullable=True)
    issue_reported_date = Column(DateTime, nullable=False)
    
    # Root Cause Analysis
    immediate_cause = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    contributing_factors = Column(JSON, nullable=True)
    
    # Analysis Method
    analysis_method = Column(String(50), nullable=True)  # 5_WHYS, FISHBONE, FMEA, AI_GENERATED
    
    # AI Analysis
    ai_analysis = Column(Text, nullable=True)
    ai_confidence_score = Column(Float, nullable=True)
    ai_suggested_causes = Column(JSON, nullable=True)
    
    # Evidence
    evidence = Column(JSON, nullable=True)  # List of evidence items
    attachments = Column(JSON, nullable=True)  # URLs to attachments
    
    # Findings
    findings_summary = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    
    # Assignment
    assigned_to = Column(String(100), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    
    # Completion
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String(100), nullable=True)
    
    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    related_feedbacks = relationship("Feedback", back_populates="rca_report", foreign_keys=[Feedback.rca_id])
    capa_actions = relationship("CAPAAction", back_populates="rca_report", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_rca_status", "status"),
        Index("idx_rca_priority", "priority"),
    )
    
    def __repr__(self):
        return f"<RCAReport(id={self.rca_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rca_id": self.rca_id,
            "status": self.status.value if self.status else None,
            "priority": self.priority,
            "problem_title": self.problem_title,
            "problem_description": self.problem_description,
            "root_cause": self.root_cause,
            "immediate_cause": self.immediate_cause,
            "contributing_factors": self.contributing_factors,
            "ai_analysis": self.ai_analysis,
            "findings_summary": self.findings_summary,
            "vehicles_affected": self.vehicles_affected_count,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CAPAAction(Base):
    """
    Corrective and Preventive Action
    Actions to address root causes
    """
    __tablename__ = "capa_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference
    capa_id = Column(String(50), unique=True, nullable=False, index=True)
    rca_id = Column(Integer, ForeignKey("rca_reports.id", ondelete="CASCADE"), nullable=False)
    
    # Type
    capa_type = Column(SQLEnum(CAPAType), nullable=False)
    
    # Status
    status = Column(SQLEnum(CAPAStatus), default=CAPAStatus.PLANNED)
    priority = Column(String(20), default="MEDIUM")
    
    # Action Details
    action_title = Column(String(200), nullable=False)
    action_description = Column(Text, nullable=False)
    expected_outcome = Column(Text, nullable=True)
    
    # Scope
    scope = Column(String(50), nullable=True)  # IMMEDIATE, SHORT_TERM, LONG_TERM
    applies_to = Column(String(100), nullable=True)  # PROCESS, SYSTEM, TRAINING, EQUIPMENT
    
    # Assignment
    assigned_to = Column(String(100), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    
    # Timeline
    planned_start_date = Column(DateTime, nullable=True)
    planned_completion_date = Column(DateTime, nullable=True)
    actual_start_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)
    
    # Implementation
    implementation_steps = Column(JSON, nullable=True)  # List of steps
    resources_required = Column(Text, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    
    # Verification
    verification_method = Column(Text, nullable=True)
    verification_date = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
    verification_result = Column(Text, nullable=True)
    effectiveness_score = Column(Float, nullable=True)  # 0-100
    
    # Evidence
    evidence_of_completion = Column(JSON, nullable=True)
    attachments = Column(JSON, nullable=True)
    
    # Closure
    closure_notes = Column(Text, nullable=True)
    closed_by = Column(String(100), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rca_report = relationship("RCAReport", back_populates="capa_actions")
    
    __table_args__ = (
        Index("idx_capa_status", "status"),
        Index("idx_capa_rca", "rca_id"),
    )
    
    def __repr__(self):
        return f"<CAPAAction(id={self.capa_id}, type={self.capa_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "capa_id": self.capa_id,
            "capa_type": self.capa_type.value if self.capa_type else None,
            "status": self.status.value if self.status else None,
            "priority": self.priority,
            "action_title": self.action_title,
            "action_description": self.action_description,
            "assigned_to": self.assigned_to,
            "planned_completion_date": self.planned_completion_date.isoformat() if self.planned_completion_date else None,
            "effectiveness_score": self.effectiveness_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }