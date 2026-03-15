"""
Behavior Agent
Driver behavior intelligence and analysis
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.agents.base_agent import BaseAgent, AgentType
from backend.services.driver_behavior_service import (
    DriverBehaviorService, get_driver_behavior_service,
)

logger = logging.getLogger(__name__)


class BehaviorAgent(BaseAgent):
    """
    Driver Behavior Intelligence Worker Agent
    Analyzes driving patterns and provides coaching recommendations
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.BEHAVIOR,
            version="1.0.0",
        )
        self._behavior_service = get_driver_behavior_service()
        logger.info("BehaviorAgent initialized")

    def get_capabilities(self) -> List[str]:
        return [
            "analyze_behavior",
            "score_driving",
            "detect_harsh_events",
            "generate_coaching_tips",
            "predict_accident_risk",
            "fuel_efficiency_analysis",
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process behavior analysis request"""
        action = input_data.get("action", "analyze_behavior")
        vehicle_id = input_data.get("vehicle_id")

        if not vehicle_id:
            return {"success": False, "error": "vehicle_id is required"}

        if action == "analyze_behavior":
            return await self._analyze_behavior(vehicle_id, input_data)
        elif action == "get_history":
            return await self._get_history(vehicle_id)
        elif action == "detect_events":
            return await self._detect_events(vehicle_id, input_data)
        else:
            return await self._analyze_behavior(vehicle_id, input_data)

    async def _analyze_behavior(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze driver behavior"""
        try:
            period_type = input_data.get("period_type", "DAILY")

            behavior = await self._behavior_service.analyze_behavior(
                vehicle_id=vehicle_id,
                period_type=period_type,
            )

            overall_score = behavior.get("overall_score", 0)
            rating = behavior.get("rating", "UNKNOWN")

            # Generate insights
            insights = []
            category_scores = behavior.get("category_scores", {})

            if category_scores.get("braking", 100) < 70:
                insights.append("Frequent harsh braking detected. Maintain safe following distance.")
            if category_scores.get("acceleration", 100) < 70:
                insights.append("Aggressive acceleration patterns observed. Gradual acceleration saves fuel.")
            if category_scores.get("speed", 100) < 70:
                insights.append("Speeding incidents recorded. Adhere to posted speed limits.")
            if category_scores.get("fuel_efficiency", 100) < 70:
                insights.append("Below-average fuel efficiency. Consider eco-driving techniques.")

            if not insights:
                insights.append("Excellent driving behavior! Keep it up.")

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "behavior_id": behavior.get("behavior_id"),
                "overall_score": overall_score,
                "rating": rating,
                "category_scores": category_scores,
                "statistics": behavior.get("statistics"),
                "events": behavior.get("events"),
                "risk_score": behavior.get("risk_score"),
                "recommendations": behavior.get("recommendations", []),
                "insights": insights,
                "trend": behavior.get("trend"),
                "decision": f"Driver rating: {rating} (Score: {overall_score})",
                "confidence": 0.82,
                "reasoning": f"Analysis based on {period_type.lower()} driving data",
            }

        except Exception as e:
            logger.error(f"Behavior analysis failed for {vehicle_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_history(self, vehicle_id: str) -> Dict[str, Any]:
        """Get behavior history"""
        try:
            history = await self._behavior_service.get_behavior_history(
                vehicle_id=vehicle_id, limit=30
            )

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "history": history,
                "record_count": len(history),
                "decision": f"Retrieved {len(history)} behavior records",
                "confidence": 1.0,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _detect_events(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect driving events from telemetry"""
        try:
            telemetry = input_data.get("telemetry_data", {})
            events = []

            # Check for harsh acceleration
            accel_x = telemetry.get("acceleration_x", 0)
            if abs(accel_x) > 3.0:
                events.append({
                    "type": "HARSH_ACCELERATION" if accel_x > 0 else "HARSH_BRAKING",
                    "severity": "HIGH" if abs(accel_x) > 5 else "MEDIUM",
                    "value": accel_x,
                    "timestamp": telemetry.get("timestamp"),
                })

            # Check for speeding
            speed = telemetry.get("speed_kmh", 0)
            if speed > 130:
                events.append({
                    "type": "SPEEDING",
                    "severity": "HIGH" if speed > 160 else "MEDIUM",
                    "value": speed,
                    "timestamp": telemetry.get("timestamp"),
                })

            # Check lateral G-force (harsh cornering)
            accel_y = telemetry.get("acceleration_y", 0)
            if abs(accel_y) > 2.0:
                events.append({
                    "type": "HARSH_CORNERING",
                    "severity": "MEDIUM",
                    "value": accel_y,
                    "timestamp": telemetry.get("timestamp"),
                })

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "events_detected": len(events),
                "events": events,
                "decision": f"Detected {len(events)} driving events",
                "confidence": 0.88,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_behavior_agent: Optional[BehaviorAgent] = None


def get_behavior_agent() -> BehaviorAgent:
    global _behavior_agent
    if _behavior_agent is None:
        _behavior_agent = BehaviorAgent()
    return _behavior_agent