"""
Diagnosis Service
Handles AI-powered vehicle diagnosis operations
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    Diagnosis, DiagnosisDetail, FailurePrediction,
    Vehicle, TelemetryData, get_async_db_context,
)
from backend.models.diagnosis import (
    RiskLevel, DiagnosisStatus, ComponentCategory,
)
from backend.telemetry.processor import RiskAnalyzer
from backend.utils.helpers import (
    generate_id, generate_reference_number, timestamp_now
)
from backend.utils.exceptions import (
    NotFoundException,
    DatabaseException,
    AgentException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class DiagnosisService:
    """
    Service for managing AI-powered diagnoses
    """

    def __init__(self):
        self.settings = get_settings()
        self.risk_analyzer = RiskAnalyzer()
        logger.info("DiagnosisService initialized")

    async def create_diagnosis(
        self,
        vehicle_id: str,
        triggered_by: str = "TELEMETRY",
        telemetry_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new diagnosis for a vehicle"""
        try:
            start_time = datetime.utcnow()
            diagnosis_id = generate_reference_number("DG")

            async with get_async_db_context() as session:
                # Get vehicle
                v_result = await session.execute(
                    select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
                )
                vehicle = v_result.scalar_one_or_none()

                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle", resource_id=vehicle_id
                    )

                # Get latest telemetry if not provided
                if not telemetry_data:
                    t_result = await session.execute(
                        select(TelemetryData)
                        .where(TelemetryData.vehicle_uuid == vehicle_id)
                        .order_by(desc(TelemetryData.timestamp))
                        .limit(1)
                    )
                    telemetry_record = t_result.scalar_one_or_none()
                    if telemetry_record:
                        telemetry_data = telemetry_record.to_dict()

                if not telemetry_data:
                    telemetry_data = self._create_default_telemetry(vehicle_id)

                # Perform risk analysis
                risk_assessment = self.risk_analyzer.analyze(telemetry_data)

                # Generate AI diagnosis
                ai_diagnosis = await self._generate_ai_diagnosis(
                    vehicle, telemetry_data, risk_assessment
                )

                # Create diagnosis record
                diagnosis = Diagnosis(
                    diagnosis_id=diagnosis_id,
                    vehicle_id=vehicle.id,
                    vehicle_uuid=vehicle_id,
                    triggered_by=triggered_by,
                    status=DiagnosisStatus.COMPLETED,
                    overall_risk_level=RiskLevel(risk_assessment.overall_risk_level),
                    confidence_score=risk_assessment.confidence_score,
                    health_score=risk_assessment.health_score,
                    summary=ai_diagnosis.get("summary"),
                    detailed_analysis=ai_diagnosis.get("detailed_analysis"),
                    recommended_actions=risk_assessment.recommended_actions,
                    predicted_failures=ai_diagnosis.get("predicted_failures"),
                    failure_probability=ai_diagnosis.get("failure_probability"),
                    estimated_days_to_failure=ai_diagnosis.get("estimated_days"),
                    affected_components=ai_diagnosis.get("affected_components"),
                    requires_immediate_attention=risk_assessment.requires_immediate_attention,
                    service_recommended=risk_assessment.health_score < 80,
                    service_urgency_days=ai_diagnosis.get("urgency_days"),
                    ml_model_used="rule_based_v1",
                    llm_model_used=self.settings.LLM_MODEL,
                    input_telemetry_summary=telemetry_data,
                    processing_started_at=start_time,
                    processing_completed_at=datetime.utcnow(),
                    processing_duration_ms=int(
                        (datetime.utcnow() - start_time).total_seconds()
                        * 1000
                    ),
                    created_at=timestamp_now(),
                )

                session.add(diagnosis)

                # Create diagnosis details
                for indicator in risk_assessment.risk_indicators:
                    detail = DiagnosisDetail(
                        diagnosis_id=0,  # Will be set after flush
                        component_category=ComponentCategory(
                            indicator.component
                        )
                        if indicator.component in [e.value for e in ComponentCategory]
                        else ComponentCategory.OTHER,
                        component_name=indicator.component,
                        status=indicator.risk_level,
                        risk_level=RiskLevel(indicator.risk_level),
                        confidence=indicator.confidence,
                        current_value=indicator.current_value,
                        threshold_warning=indicator.threshold_warning,
                        threshold_critical=indicator.threshold_critical,
                        issue_description=indicator.message,
                        recommended_action=f"Service required for {indicator.component}",
                    )
                    diagnosis.details.append(detail)

                # Create failure predictions
                for i, failure in enumerate(
                    ai_diagnosis.get("predicted_failures", [])
                ):
                    prediction = FailurePrediction(
                        prediction_id=generate_reference_number("FP"),
                        component_category=ComponentCategory.OTHER,
                        component_name=failure.get("component", "Unknown"),
                        failure_type=failure.get("type", "Unknown"),
                        failure_description=failure.get("description"),
                        probability=failure.get("probability", 0.5),
                        estimated_days_to_failure=failure.get("days"),
                        severity=RiskLevel(
                            failure.get("severity", RiskLevel.MEDIUM)
                        ),
                        safety_impact=failure.get("safety_impact", False),
                        breakdown_risk=failure.get("breakdown_risk", False),
                    )
                    diagnosis.failure_predictions.append(prediction)

                await session.flush()
                await session.commit()
                await session.refresh(diagnosis)

                # Update vehicle health
                vehicle.update_health_status(risk_assessment.health_score)
                vehicle.updated_at = timestamp_now()
                await session.commit()

                logger.info(
                    f"Created diagnosis {diagnosis_id} for vehicle {vehicle_id}"
                )
                return diagnosis.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error creating diagnosis for {vehicle_id}: {e}")
            raise AgentException(
                message="Failed to create diagnosis",
                agent_type="DIAGNOSIS_AGENT",
                action="diagnose",
            )

    async def get_diagnosis(self, diagnosis_id: str) -> Dict[str, Any]:
        """Get a diagnosis by ID"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Diagnosis).where(
                        Diagnosis.diagnosis_id == diagnosis_id
                    )
                )
                diagnosis = result.scalar_one_or_none()

                if not diagnosis:
                    raise NotFoundException(
                        resource="Diagnosis", resource_id=diagnosis_id
                    )

                return diagnosis.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting diagnosis {diagnosis_id}: {e}")
            raise DatabaseException(
                message="Failed to get diagnosis",
                operation="read",
                original_error=e,
            )

    async def get_vehicle_diagnoses(
        self,
        vehicle_id: str,
        page: int = 1,
        page_size: int = 10,
        risk_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get diagnoses for a vehicle"""
        try:
            async with get_async_db_context() as session:
                query = select(Diagnosis).where(
                    Diagnosis.vehicle_uuid == vehicle_id
                )
                count_query = select(func.count(Diagnosis.id)).where(
                    Diagnosis.vehicle_uuid == vehicle_id
                )

                if risk_level:
                    query = query.where(
                        Diagnosis.overall_risk_level == RiskLevel(risk_level)
                    )
                    count_query = count_query.where(
                        Diagnosis.overall_risk_level == RiskLevel(risk_level)
                    )

                # Count
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                # Fetch
                offset = (page - 1) * page_size
                query = (
                    query.order_by(desc(Diagnosis.created_at))
                    .offset(offset)
                    .limit(page_size)
                )

                result = await session.execute(query)
                diagnoses = result.scalars().all()

                total_pages = (total + page_size - 1) // page_size

                return {
                    "success": True,
                    "data": [d.to_dict() for d in diagnoses],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(
                f"Error getting diagnoses for vehicle {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get vehicle diagnoses",
                operation="read",
                original_error=e,
            )

    async def get_recent_diagnoses(
        self, limit: int = 20, risk_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent diagnoses across all vehicles"""
        try:
            async with get_async_db_context() as session:
                query = select(Diagnosis)

                if risk_level:
                    query = query.where(
                        Diagnosis.overall_risk_level == RiskLevel(risk_level)
                    )

                query = (
                    query.order_by(desc(Diagnosis.created_at)).limit(limit)
                )

                result = await session.execute(query)
                diagnoses = result.scalars().all()

                return [d.to_dict() for d in diagnoses]

        except Exception as e:
            logger.error(f"Error getting recent diagnoses: {e}")
            raise DatabaseException(
                message="Failed to get recent diagnoses",
                operation="read",
                original_error=e,
            )

    async def _generate_ai_diagnosis(
        self,
        vehicle: Vehicle,
        telemetry: Dict[str, Any],
        risk_assessment: Any,
    ) -> Dict[str, Any]:
        """Generate AI-powered diagnosis"""
        predicted_failures = []
        affected_components = []

        for indicator in risk_assessment.risk_indicators:
            affected_components.append(indicator.component)

            if indicator.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                days_estimate = 7 if indicator.risk_level == RiskLevel.CRITICAL else 21

                predicted_failures.append(
                    {
                        "component": indicator.component,
                        "type": f"{indicator.component} failure",
                        "description": indicator.message,
                        "probability": 0.85
                        if indicator.risk_level == RiskLevel.CRITICAL
                        else 0.60,
                        "days": days_estimate,
                        "severity": indicator.risk_level,
                        "safety_impact": indicator.component
                        in ["BRAKES", "ENGINE", "TIRES"],
                        "breakdown_risk": indicator.risk_level
                        == RiskLevel.CRITICAL,
                    }
                )

        max_probability = (
            max(f["probability"] for f in predicted_failures)
            if predicted_failures
            else 0.1
        )
        min_days = (
            min(f["days"] for f in predicted_failures)
            if predicted_failures
            else 90
        )

        # Generate summary
        if risk_assessment.overall_risk_level == RiskLevel.CRITICAL:
            summary = (
                f"CRITICAL: Vehicle {vehicle.vehicle_id} ({vehicle.make} "
                f"{vehicle.model} {vehicle.year}) requires immediate attention. "
                f"Health score: {risk_assessment.health_score}/100. "
                f"{len(predicted_failures)} potential failures detected."
            )
            urgency_days = 3
        elif risk_assessment.overall_risk_level == RiskLevel.HIGH:
            summary = (
                f"HIGH RISK: Vehicle {vehicle.vehicle_id} has significant issues. "
                f"Health score: {risk_assessment.health_score}/100. "
                f"Service recommended within 7 days."
            )
            urgency_days = 7
        elif risk_assessment.overall_risk_level == RiskLevel.MEDIUM:
            summary = (
                f"MODERATE: Vehicle {vehicle.vehicle_id} has minor issues to monitor. "
                f"Health score: {risk_assessment.health_score}/100. "
                f"Schedule service within 30 days."
            )
            urgency_days = 30
        else:
            summary = (
                f"HEALTHY: Vehicle {vehicle.vehicle_id} is in good condition. "
                f"Health score: {risk_assessment.health_score}/100. "
                f"No immediate action required."
            )
            urgency_days = 90

        return {
            "summary": summary,
            "detailed_analysis": f"Analysis based on {len(risk_assessment.risk_indicators)} risk indicators.",
            "predicted_failures": predicted_failures,
            "failure_probability": max_probability,
            "estimated_days": min_days,
            "affected_components": list(set(affected_components)),
            "urgency_days": urgency_days,
        }

    def _create_default_telemetry(self, vehicle_id: str) -> Dict[str, Any]:
        """Create default telemetry data"""
        return {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.utcnow().isoformat(),
            "engine_temperature_celsius": 90.0,
            "battery_voltage": 12.6,
            "oil_level_percent": 75.0,
            "brake_pad_wear_front_percent": 30.0,
            "brake_pad_wear_rear_percent": 25.0,
            "fuel_level_percent": 60.0,
            "speed_kmh": 0,
        }


# Singleton instance
_diagnosis_service: Optional[DiagnosisService] = None


def get_diagnosis_service() -> DiagnosisService:
    """Get or create diagnosis service instance"""
    global _diagnosis_service
    if _diagnosis_service is None:
        _diagnosis_service = DiagnosisService()
    return _diagnosis_service