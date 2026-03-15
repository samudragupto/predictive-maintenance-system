"""
Scheduling Agent
Intelligent service appointment scheduling
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from backend.agents.base_agent import BaseAgent, AgentType
from backend.services.appointment_service import AppointmentService, get_appointment_service
from backend.services.service_center_service import ServiceCenterService, get_service_center_service

logger = logging.getLogger(__name__)


class SchedulingAgent(BaseAgent):
    """
    Smart Scheduling Worker Agent
    Automatically schedules service appointments based on:
    - Failure severity
    - Service center availability
    - Vehicle location and driver preferences
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.SCHEDULING,
            version="1.0.0",
        )
        self._appointment_service = get_appointment_service()
        self._center_service = get_service_center_service()
        logger.info("SchedulingAgent initialized")

    def get_capabilities(self) -> List[str]:
        return [
            "auto_schedule",
            "find_optimal_slot",
            "reschedule_appointment",
            "check_availability",
            "prioritize_urgent_services",
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process scheduling request"""
        action = input_data.get("action", "auto_schedule")
        vehicle_id = input_data.get("vehicle_id")

        if not vehicle_id:
            return {"success": False, "error": "vehicle_id is required"}

        if action == "auto_schedule":
            return await self._auto_schedule(vehicle_id, input_data)
        elif action == "find_slot":
            return await self._find_optimal_slot(vehicle_id, input_data)
        elif action == "check_availability":
            return await self._check_availability(input_data)
        else:
            return await self._auto_schedule(vehicle_id, input_data)

    async def _auto_schedule(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically schedule a service appointment"""
        try:
            urgency = input_data.get("urgency", "MEDIUM")
            diagnosis_id = input_data.get("diagnosis_id")

            result = await self._appointment_service.auto_schedule(
                vehicle_id=vehicle_id,
                diagnosis_id=diagnosis_id,
                urgency=urgency,
            )

            urgency_text = {
                "CRITICAL": "within 24 hours",
                "HIGH": "within 3 days",
                "MEDIUM": "within 7 days",
                "LOW": "within 14 days",
            }

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "appointment_id": result.get("appointment_id"),
                "scheduled_date": result.get("scheduled_date"),
                "service_center": result.get("service_center_name"),
                "urgency": urgency,
                "auto_scheduled": True,
                "decision": f"Scheduled {urgency.lower()} priority service {urgency_text.get(urgency, '')}",
                "confidence": 0.90,
                "reasoning": f"Auto-scheduled based on {urgency} urgency level",
            }

        except Exception as e:
            logger.error(f"Auto-scheduling failed for {vehicle_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _find_optimal_slot(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find the optimal time slot"""
        try:
            urgency = input_data.get("urgency", "MEDIUM")
            preferred_date = input_data.get("preferred_date")

            # Get available centers
            centers = await self._center_service.get_all_centers(status="ACTIVE")

            if not centers:
                return {
                    "success": False,
                    "error": "No active service centers available",
                }

            # Calculate optimal date
            urgency_days = {"CRITICAL": 1, "HIGH": 3, "MEDIUM": 7, "LOW": 14}
            days_out = urgency_days.get(urgency, 7)
            optimal_date = datetime.utcnow() + timedelta(days=days_out)
            optimal_date = optimal_date.replace(hour=9, minute=0, second=0)

            # Skip weekends
            while optimal_date.weekday() >= 5:
                optimal_date += timedelta(days=1)

            # Generate alternative slots
            alternatives = []
            for i in range(3):
                alt_date = optimal_date + timedelta(days=i + 1)
                while alt_date.weekday() >= 5:
                    alt_date += timedelta(days=1)
                alternatives.append({
                    "date": alt_date.isoformat(),
                    "time": "09:00",
                    "center": centers[i % len(centers)].get("name", "N/A") if isinstance(centers[i % len(centers)], dict) else "Service Center",
                })

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "optimal_slot": {
                    "date": optimal_date.isoformat(),
                    "time": "09:00",
                    "center": centers[0].get("name", "N/A") if isinstance(centers[0], dict) else "Service Center",
                },
                "alternatives": alternatives,
                "decision": f"Optimal slot: {optimal_date.strftime('%Y-%m-%d')} at 09:00",
                "confidence": 0.85,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_availability(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check service center availability"""
        try:
            centers = await self._center_service.get_all_centers(status="ACTIVE")

            return {
                "success": True,
                "available_centers": len(centers),
                "centers": centers[:5],
                "decision": f"{len(centers)} centers available",
                "confidence": 1.0,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_scheduling_agent: Optional[SchedulingAgent] = None


def get_scheduling_agent() -> SchedulingAgent:
    global _scheduling_agent
    if _scheduling_agent is None:
        _scheduling_agent = SchedulingAgent()
    return _scheduling_agent