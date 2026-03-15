"""
Security Log Model
UEBA (User and Entity Behavior Analytics) and audit logging
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


class LogLevel(str, enum.Enum):
    """Log severity level"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ActionType(str, enum.Enum):
    """Type of action performed"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    API_CALL = "API_CALL"
    AGENT_ACTION = "AGENT_ACTION"
    SCHEDULE = "SCHEDULE"
    DIAGNOSE = "DIAGNOSE"
    ESTIMATE = "ESTIMATE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


class AlertSeverity(str, enum.Enum):
    """Alert severity level"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class SecurityLog(Base):
    """
    Security Log Entity
    General security and audit logging
    """
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Log Identification
    log_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Level
    level = Column(SQLEnum(LogLevel), default=LogLevel.INFO)
    
    # Actor (Who performed the action)
    actor_type = Column(String(50), nullable=False)  # USER, AGENT, SYSTEM, API_CLIENT
    actor_id = Column(String(100), nullable=True, index=True)
    actor_name = Column(String(100), nullable=True)
    actor_role = Column(String(50), nullable=True)
    
    # Action
    action_type = Column(SQLEnum(ActionType), nullable=False)
    action_name = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=True)
    
    # Resource (What was affected)
    resource_type = Column(String(50), nullable=True)  # VEHICLE, DIAGNOSIS, APPOINTMENT, etc.
    resource_id = Column(String(100), nullable=True, index=True)
    resource_name = Column(String(200), nullable=True)
    
    # Request Details
    request_id = Column(String(100), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)
    request_params = Column(JSON, nullable=True)
    request_body_summary = Column(Text, nullable=True)  # Sanitized summary
    
    # Response
    response_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    
    # Location
    geo_country = Column(String(100), nullable=True)
    geo_city = Column(String(100), nullable=True)
    
    # Additional Data
    meta_data = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index("idx_seclog_timestamp", "timestamp"),
        Index("idx_seclog_actor", "actor_type", "actor_id"),
        Index("idx_seclog_action", "action_type"),
        Index("idx_seclog_resource", "resource_type", "resource_id"),
        Index("idx_seclog_level", "level"),
    )
    
    def __repr__(self):
        return f"<SecurityLog(id={self.log_id}, action={self.action_name}, actor={self.actor_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level.value if self.level else None,
            "actor": {
                "type": self.actor_type,
                "id": self.actor_id,
                "name": self.actor_name,
            },
            "action": {
                "type": self.action_type.value if self.action_type else None,
                "name": self.action_name,
                "description": self.action_description,
            },
            "resource": {
                "type": self.resource_type,
                "id": self.resource_id,
            },
            "success": self.success,
            "error": self.error_message if not self.success else None,
            "ip_address": self.ip_address,
        }


class AgentAuditLog(Base):
    """
    Agent Audit Log
    Tracks all AI agent actions for compliance and debugging
    """
    __tablename__ = "agent_audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Log Identification
    audit_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Agent Information
    agent_type = Column(String(50), nullable=False, index=True)
    # MASTER_AGENT, DIAGNOSIS_AGENT, COST_AGENT, SCHEDULING_AGENT, BEHAVIOR_AGENT, FEEDBACK_AGENT
    agent_id = Column(String(100), nullable=False)
    agent_version = Column(String(20), nullable=True)
    
    # Action
    action = Column(String(100), nullable=False)
    action_category = Column(String(50), nullable=True)  # ANALYSIS, DECISION, COMMUNICATION, etc.
    
    # Input
    input_data = Column(JSON, nullable=True)
    input_summary = Column(Text, nullable=True)
    
    # Processing
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # LLM Details (if applicable)
    llm_model_used = Column(String(100), nullable=True)
    llm_prompt = Column(Text, nullable=True)
    llm_tokens_used = Column(Integer, nullable=True)
    llm_cost_usd = Column(Float, nullable=True)
    
    # ML Model Details (if applicable)
    ml_model_used = Column(String(100), nullable=True)
    ml_model_version = Column(String(50), nullable=True)
    ml_confidence_score = Column(Float, nullable=True)
    
    # Output
    output_data = Column(JSON, nullable=True)
    output_summary = Column(Text, nullable=True)
    
    # Decision
    decision_made = Column(String(200), nullable=True)
    decision_confidence = Column(Float, nullable=True)
    decision_reasoning = Column(Text, nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Impact
    affected_vehicle_id = Column(String(50), nullable=True, index=True)
    affected_resources = Column(JSON, nullable=True)
    
    # UEBA Scoring
    anomaly_score = Column(Float, nullable=True)  # 0.0 to 1.0
    is_anomalous = Column(Boolean, default=False)
    
    # Human Override
    human_review_required = Column(Boolean, default=False)
    human_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_decision = Column(String(50), nullable=True)  # APPROVED, REJECTED, MODIFIED
    review_notes = Column(Text, nullable=True)
    
    # Correlation
    correlation_id = Column(String(100), nullable=True, index=True)
    parent_audit_id = Column(String(50), nullable=True)  # For chained agent calls
    
    __table_args__ = (
        Index("idx_agent_audit_time", "timestamp"),
        Index("idx_agent_audit_type", "agent_type"),
        Index("idx_agent_audit_action", "action"),
        Index("idx_agent_audit_vehicle", "affected_vehicle_id"),
        Index("idx_agent_audit_anomaly", "is_anomalous"),
    )
    
    def __repr__(self):
        return f"<AgentAuditLog(id={self.audit_id}, agent={self.agent_type}, action={self.action})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent": {
                "type": self.agent_type,
                "id": self.agent_id,
                "version": self.agent_version,
            },
            "action": self.action,
            "processing_duration_ms": self.processing_duration_ms,
            "decision": {
                "made": self.decision_made,
                "confidence": self.decision_confidence,
                "reasoning": self.decision_reasoning,
            },
            "success": self.success,
            "anomaly_score": self.anomaly_score,
            "is_anomalous": self.is_anomalous,
            "human_review_required": self.human_review_required,
        }


class UEBAAlert(Base):
    """
    UEBA Alert
    User and Entity Behavior Analytics alerts
    """
    __tablename__ = "ueba_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Alert Identification
    alert_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Timestamp
    detected_at = Column(DateTime, nullable=False, index=True)
    
    # Severity
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.OPEN, index=True)
    
    # Alert Type
    alert_type = Column(String(100), nullable=False)
    # Examples: UNUSUAL_ACCESS_PATTERN, ANOMALOUS_AGENT_BEHAVIOR, SUSPICIOUS_DATA_ACCESS,
    #           IMPOSSIBLE_TRAVEL, PRIVILEGE_ESCALATION, DATA_EXFILTRATION_ATTEMPT
    alert_category = Column(String(50), nullable=True)  # BEHAVIORAL, ACCESS, DATA, SYSTEM
    
    # Description
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Entity Involved
    entity_type = Column(String(50), nullable=False)  # USER, AGENT, SYSTEM, DEVICE
    entity_id = Column(String(100), nullable=False, index=True)
    entity_name = Column(String(100), nullable=True)
    
    # Anomaly Details
    anomaly_score = Column(Float, nullable=False)  # 0.0 to 1.0
    baseline_behavior = Column(JSON, nullable=True)
    observed_behavior = Column(JSON, nullable=True)
    deviation_details = Column(Text, nullable=True)
    
    # Risk Assessment
    risk_score = Column(Float, nullable=True)  # 0-100
    potential_impact = Column(Text, nullable=True)
    affected_resources = Column(JSON, nullable=True)
    
    # Evidence
    related_events = Column(JSON, nullable=True)  # List of related log IDs
    evidence_summary = Column(Text, nullable=True)
    audit_log_ids = Column(JSON, nullable=True)
    
    # Automated Response
    auto_response_taken = Column(Boolean, default=False)
    auto_response_action = Column(String(100), nullable=True)  # BLOCKED, RATE_LIMITED, NOTIFIED
    auto_response_timestamp = Column(DateTime, nullable=True)
    
    # Investigation
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_action = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # False Positive Handling
    is_false_positive = Column(Boolean, default=False)
    false_positive_reason = Column(Text, nullable=True)
    added_to_whitelist = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_ueba_detected", "detected_at"),
        Index("idx_ueba_severity", "severity"),
        Index("idx_ueba_status", "status"),
        Index("idx_ueba_entity", "entity_type", "entity_id"),
        Index("idx_ueba_type", "alert_type"),
    )
    
    def __repr__(self):
        return f"<UEBAAlert(id={self.alert_id}, severity={self.severity}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "alert_type": self.alert_type,
            "title": self.title,
            "description": self.description,
            "entity": {
                "type": self.entity_type,
                "id": self.entity_id,
                "name": self.entity_name,
            },
            "anomaly_score": self.anomaly_score,
            "risk_score": self.risk_score,
            "auto_response_taken": self.auto_response_taken,
            "auto_response_action": self.auto_response_action,
            "is_false_positive": self.is_false_positive,
        }