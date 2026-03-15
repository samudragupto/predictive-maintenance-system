"""
Security Service
Handles security logging and UEBA monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    SecurityLog, AgentAuditLog, UEBAAlert, get_async_db_context,
)
from backend.models.security_log import (
    LogLevel, ActionType, AlertSeverity, AlertStatus,
)
from backend.utils.helpers import generate_reference_number, timestamp_now
from backend.utils.exceptions import NotFoundException, DatabaseException

settings = get_settings()
logger = logging.getLogger(__name__)


class SecurityService:
    """
    Service for security logging and UEBA monitoring
    """

    def __init__(self):
        self.settings = get_settings()
        self._anomaly_threshold = self.settings.UEBA_ANOMALY_THRESHOLD
        self._blocking_threshold = self.settings.UEBA_BLOCKING_THRESHOLD
        logger.info("SecurityService initialized")

    async def log_action(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log a security action"""
        try:
            log_id = generate_reference_number("SL")

            async with get_async_db_context() as session:
                log_entry = SecurityLog(
                    log_id=log_id,
                    timestamp=timestamp_now(),
                    level=LogLevel(data.get("level", "INFO")),
                    actor_type=data.get("actor_type", "SYSTEM"),
                    actor_id=data.get("actor_id"),
                    actor_name=data.get("actor_name"),
                    actor_role=data.get("actor_role"),
                    action_type=ActionType(
                        data.get("action_type", "API_CALL")
                    ),
                    action_name=data.get("action_name", "unknown"),
                    action_description=data.get("action_description"),
                    resource_type=data.get("resource_type"),
                    resource_id=data.get("resource_id"),
                    request_method=data.get("request_method"),
                    request_path=data.get("request_path"),
                    response_status_code=data.get(
                        "response_status_code"
                    ),
                    response_time_ms=data.get("response_time_ms"),
                    success=data.get("success", True),
                    error_message=data.get("error_message"),
                    ip_address=data.get("ip_address"),
                    user_agent=data.get("user_agent"),
                    correlation_id=data.get("correlation_id"),
                )

                session.add(log_entry)
                await session.commit()

                return log_entry.to_dict()

        except Exception as e:
            logger.error(f"Error logging security action: {e}")
            # Don't raise - security logging should not break the app
            return {"error": str(e)}

    async def log_agent_action(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log an AI agent action"""
        try:
            audit_id = generate_reference_number("AA")

            async with get_async_db_context() as session:
                # Calculate anomaly score
                anomaly_score = await self._calculate_anomaly_score(
                    data
                )
                is_anomalous = anomaly_score > self._anomaly_threshold

                audit_entry = AgentAuditLog(
                    audit_id=audit_id,
                    timestamp=timestamp_now(),
                    agent_type=data.get("agent_type"),
                    agent_id=data.get("agent_id", str(uuid.uuid4())),
                    agent_version=data.get("agent_version", "1.0"),
                    action=data.get("action"),
                    action_category=data.get("action_category"),
                    input_summary=data.get("input_summary"),
                    processing_duration_ms=data.get(
                        "processing_duration_ms"
                    ),
                    llm_model_used=data.get("llm_model_used"),
                    llm_tokens_used=data.get("llm_tokens_used"),
                    output_summary=data.get("output_summary"),
                    decision_made=data.get("decision_made"),
                    decision_confidence=data.get(
                        "decision_confidence"
                    ),
                    decision_reasoning=data.get("decision_reasoning"),
                    success=data.get("success", True),
                    error_message=data.get("error_message"),
                    affected_vehicle_id=data.get(
                        "affected_vehicle_id"
                    ),
                    anomaly_score=anomaly_score,
                    is_anomalous=is_anomalous,
                    human_review_required=anomaly_score
                    > self._blocking_threshold,
                    correlation_id=data.get("correlation_id"),
                )

                session.add(audit_entry)
                await session.commit()

                # Create UEBA alert if anomalous
                if is_anomalous:
                    await self._create_ueba_alert(
                        session, audit_entry, anomaly_score
                    )

                return audit_entry.to_dict()

        except Exception as e:
            logger.error(f"Error logging agent action: {e}")
            return {"error": str(e)}

    async def get_security_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        level: Optional[str] = None,
        actor_type: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get security logs"""
        try:
            async with get_async_db_context() as session:
                query = select(SecurityLog)
                count_query = select(func.count(SecurityLog.id))

                if level:
                    query = query.where(
                        SecurityLog.level == LogLevel(level)
                    )
                    count_query = count_query.where(
                        SecurityLog.level == LogLevel(level)
                    )

                if actor_type:
                    query = query.where(
                        SecurityLog.actor_type == actor_type
                    )
                    count_query = count_query.where(
                        SecurityLog.actor_type == actor_type
                    )

                if action_type:
                    query = query.where(
                        SecurityLog.action_type == ActionType(action_type)
                    )
                    count_query = count_query.where(
                        SecurityLog.action_type == ActionType(action_type)
                    )

                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                offset = (page - 1) * page_size
                query = (
                    query.order_by(desc(SecurityLog.timestamp))
                    .offset(offset)
                    .limit(page_size)
                )

                result = await session.execute(query)
                logs = result.scalars().all()

                return {
                    "success": True,
                    "data": [l.to_dict() for l in logs],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1)
                    // page_size,
                }

        except Exception as e:
            logger.error(f"Error getting security logs: {e}")
            raise DatabaseException(
                message="Failed to get security logs",
                operation="read",
                original_error=e,
            )

    async def get_ueba_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get UEBA alerts"""
        try:
            async with get_async_db_context() as session:
                query = select(UEBAAlert)

                if status:
                    query = query.where(
                        UEBAAlert.status == AlertStatus(status)
                    )
                if severity:
                    query = query.where(
                        UEBAAlert.severity == AlertSeverity(severity)
                    )

                query = (
                    query.order_by(desc(UEBAAlert.detected_at))
                    .limit(limit)
                )

                result = await session.execute(query)
                alerts = result.scalars().all()

                return [a.to_dict() for a in alerts]

        except Exception as e:
            logger.error(f"Error getting UEBA alerts: {e}")
            raise DatabaseException(
                message="Failed to get UEBA alerts",
                operation="read",
                original_error=e,
            )

    async def update_ueba_alert(
        self,
        alert_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a UEBA alert"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(UEBAAlert).where(
                        UEBAAlert.alert_id == alert_id
                    )
                )
                alert = result.scalar_one_or_none()

                if not alert:
                    raise NotFoundException(
                        resource="UEBA Alert",
                        resource_id=alert_id,
                    )

                if "status" in data:
                    alert.status = AlertStatus(data["status"])
                if "investigation_notes" in data:
                    alert.investigation_notes = data[
                        "investigation_notes"
                    ]
                if "is_false_positive" in data:
                    alert.is_false_positive = data["is_false_positive"]
                    if data["is_false_positive"]:
                        alert.status = AlertStatus.FALSE_POSITIVE
                        alert.false_positive_reason = data.get(
                            "false_positive_reason"
                        )

                if data.get("status") == "ACKNOWLEDGED":
                    alert.acknowledged_at = timestamp_now()
                    alert.acknowledged_by = data.get(
                        "acknowledged_by", "admin"
                    )
                elif data.get("status") == "RESOLVED":
                    alert.resolved_at = timestamp_now()
                    alert.resolved_by = data.get(
                        "resolved_by", "admin"
                    )
                    alert.resolution_notes = data.get(
                        "resolution_notes"
                    )

                alert.updated_at = timestamp_now()
                await session.commit()
                await session.refresh(alert)

                return alert.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating UEBA alert: {e}")
            raise DatabaseException(
                message="Failed to update UEBA alert",
                operation="update",
                original_error=e,
            )

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary for dashboard"""
        try:
            async with get_async_db_context() as session:
                total_result = await session.execute(
                    select(func.count(UEBAAlert.id))
                )
                total = total_result.scalar() or 0

                critical_result = await session.execute(
                    select(func.count(UEBAAlert.id)).where(
                        UEBAAlert.severity == AlertSeverity.CRITICAL
                    )
                )
                critical = critical_result.scalar() or 0

                high_result = await session.execute(
                    select(func.count(UEBAAlert.id)).where(
                        UEBAAlert.severity == AlertSeverity.HIGH
                    )
                )
                high = high_result.scalar() or 0

                open_result = await session.execute(
                    select(func.count(UEBAAlert.id)).where(
                        UEBAAlert.status == AlertStatus.OPEN
                    )
                )
                unacknowledged = open_result.scalar() or 0

                return {
                    "total_alerts": total,
                    "critical_alerts": critical,
                    "high_alerts": high,
                    "medium_alerts": total - critical - high,
                    "low_alerts": 0,
                    "unacknowledged": unacknowledged,
                }

        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            raise DatabaseException(
                message="Failed to get alert summary",
                operation="read",
                original_error=e,
            )

    async def _calculate_anomaly_score(
        self, data: Dict[str, Any]
    ) -> float:
        """Calculate anomaly score for an agent action"""
        score = 0.0

        # Check processing time
        processing_time = data.get("processing_duration_ms", 0)
        if processing_time > 30000:  # Over 30 seconds
            score += 0.3
        elif processing_time > 10000:
            score += 0.1

        # Check token usage
        tokens = data.get("llm_tokens_used", 0)
        if tokens > 10000:
            score += 0.2
        elif tokens > 5000:
            score += 0.1

        # Check if action failed
        if not data.get("success", True):
            score += 0.2

        # Check confidence
        confidence = data.get("decision_confidence", 1.0)
        if confidence and confidence < 0.3:
            score += 0.2

        return min(score, 1.0)

    async def _create_ueba_alert(
        self,
        session: AsyncSession,
        audit: AgentAuditLog,
        anomaly_score: float,
    ) -> None:
        """Create a UEBA alert"""
        try:
            alert_id = generate_reference_number("UA")

            # Determine severity
            if anomaly_score >= self._blocking_threshold:
                severity = AlertSeverity.CRITICAL
                auto_action = "BLOCKED"
            elif anomaly_score >= 0.9:
                severity = AlertSeverity.HIGH
                auto_action = "RATE_LIMITED"
            else:
                severity = AlertSeverity.MEDIUM
                auto_action = "NOTIFIED"

            alert = UEBAAlert(
                alert_id=alert_id,
                detected_at=timestamp_now(),
                severity=severity,
                status=AlertStatus.OPEN,
                alert_type="ANOMALOUS_AGENT_BEHAVIOR",
                alert_category="BEHAVIORAL",
                title=f"Anomalous behavior detected: {audit.agent_type}",
                description=(
                    f"Agent {audit.agent_type} performed action '{audit.action}' "
                    f"with anomaly score {anomaly_score:.2f}. "
                    f"Decision: {audit.decision_made}"
                ),
                entity_type="AGENT",
                entity_id=audit.agent_id,
                entity_name=audit.agent_type,
                anomaly_score=anomaly_score,
                risk_score=anomaly_score * 100,
                audit_log_ids=[audit.audit_id],
                auto_response_taken=True,
                auto_response_action=auto_action,
                auto_response_timestamp=timestamp_now(),
                created_at=timestamp_now(),
            )

            session.add(alert)
            await session.commit()

            logger.warning(
                f"UEBA Alert created: {alert_id}, severity={severity.value}"
            )

        except Exception as e:
            logger.error(f"Error creating UEBA alert: {e}")


# Singleton instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get or create security service instance"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service