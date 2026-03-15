"""
Diagnosis Agent
AI-powered vehicle diagnosis and failure prediction
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.agents.base_agent import BaseAgent, AgentType
from backend.services.diagnosis_service import DiagnosisService, get_diagnosis_service
from backend.services.telemetry_service import TelemetryService, get_telemetry_service
from backend.utils.helpers import timestamp_now

logger = logging.getLogger(__name__)


class DiagnosisAgent(BaseAgent):
    """
    Diagnosis Worker Agent
    Analyzes vehicle telemetry and generates diagnoses
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.DIAGNOSIS,
            version="1.0.0",
        )
        self._diagnosis_service = get_diagnosis_service()
        self._telemetry_service = get_telemetry_service()
        logger.info("DiagnosisAgent initialized")

    def get_capabilities(self) -> List[str]:
        return [
            "diagnose_vehicle",
            "predict_failures",
            "assess_risk_level",
            "generate_recommendations",
            "analyze_dtc_codes",
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process diagnosis request"""
        action = input_data.get("action", "diagnose_vehicle")
        vehicle_id = input_data.get("vehicle_id")

        if not vehicle_id:
            return {"success": False, "error": "vehicle_id is required"}

        if action == "diagnose_vehicle":
            return await self._diagnose_vehicle(vehicle_id, input_data)
        elif action == "predict_failures":
            return await self._predict_failures(vehicle_id, input_data)
        elif action == "assess_risk":
            return await self._assess_risk(vehicle_id)
        else:
            return await self._diagnose_vehicle(vehicle_id, input_data)

    async def _diagnose_vehicle(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform vehicle diagnosis"""
        try:
            telemetry_data = input_data.get("telemetry_data")

            # Create diagnosis through service
            diagnosis = await self._diagnosis_service.create_diagnosis(
                vehicle_id=vehicle_id,
                triggered_by="AGENT",
                telemetry_data=telemetry_data,
            )

            risk_level = diagnosis.get("overall_risk_level", "LOW")

            return {
                "success": True,
                "diagnosis_id": diagnosis.get("diagnosis_id"),
                "vehicle_id": vehicle_id,
                "risk_level": risk_level,
                "health_score": diagnosis.get("health_score"),
                "confidence_score": diagnosis.get("confidence_score"),
                "summary": diagnosis.get("summary"),
                "predicted_failures": diagnosis.get("predicted_failures", []),
                "affected_components": diagnosis.get("affected_components", []),
                "recommended_actions": diagnosis.get("recommended_actions", []),
                "requires_immediate_attention": diagnosis.get("requires_immediate_attention", False),
                "service_recommended": diagnosis.get("service_recommended", False),
                "decision": f"Risk level: {risk_level}",
                "confidence": diagnosis.get("confidence_score", 0.85),
                "reasoning": f"Analysis based on telemetry data for vehicle {vehicle_id}",
            }

        except Exception as e:
            logger.error(f"Diagnosis failed for {vehicle_id}: {e}")
            return {
                "success": False,
                "vehicle_id": vehicle_id,
                "error": str(e),
            }

    async def _predict_failures(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict potential failures"""
        try:
            # Get risk analysis from telemetry
            risk_analysis = await self._telemetry_service.get_risk_analysis(vehicle_id)

            predictions = []
            for indicator in risk_analysis.get("risk_indicators", []):
                if indicator.get("risk_level") in ["HIGH", "CRITICAL"]:
                    predictions.append({
                        "component": indicator.get("component"),
                        "failure_type": f"{indicator.get('component')} degradation",
                        "probability": 0.85 if indicator.get("risk_level") == "CRITICAL" else 0.60,
                        "estimated_days": 7 if indicator.get("risk_level") == "CRITICAL" else 21,
                        "message": indicator.get("message"),
                    })

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "predictions": predictions,
                "prediction_count": len(predictions),
                "decision": f"Found {len(predictions)} potential failures",
                "confidence": 0.80,
            }

        except Exception as e:
            logger.error(f"Failure prediction failed for {vehicle_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _assess_risk(self, vehicle_id: str) -> Dict[str, Any]:
        """Assess current risk level"""
        try:
            risk_analysis = await self._telemetry_service.get_risk_analysis(vehicle_id)
            return {
                "success": True,
                "vehicle_id": vehicle_id,
                **risk_analysis,
                "decision": f"Risk level: {risk_analysis.get('overall_risk_level')}",
                "confidence": risk_analysis.get("confidence_score", 0.85),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_diagnosis_agent: Optional[DiagnosisAgent] = None


def get_diagnosis_agent() -> DiagnosisAgent:
    global _diagnosis_agent
    if _diagnosis_agent is None:
        _diagnosis_agent = DiagnosisAgent()
    return _diagnosis_agent