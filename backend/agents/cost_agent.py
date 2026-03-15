"""
Cost Estimation Agent
AI-driven cost estimation for vehicle service and repairs
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.agents.base_agent import BaseAgent, AgentType
from backend.services.cost_service import CostEstimationService, get_cost_service

logger = logging.getLogger(__name__)


class CostAgent(BaseAgent):
    """
    Cost Estimation Worker Agent
    Generates cost estimates for repairs and maintenance
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.COST,
            version="1.0.0",
        )
        self._cost_service = get_cost_service()
        logger.info("CostAgent initialized")

    def get_capabilities(self) -> List[str]:
        return [
            "estimate_cost",
            "compare_costs",
            "forecast_warranty_costs",
            "optimize_parts_selection",
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process cost estimation request"""
        action = input_data.get("action", "estimate_cost")
        vehicle_id = input_data.get("vehicle_id")

        if not vehicle_id:
            return {"success": False, "error": "vehicle_id is required"}

        if action == "estimate_cost":
            return await self._estimate_cost(vehicle_id, input_data)
        elif action == "compare_costs":
            return await self._compare_costs(vehicle_id, input_data)
        else:
            return await self._estimate_cost(vehicle_id, input_data)

    async def _estimate_cost(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate cost estimate"""
        try:
            diagnosis_id = input_data.get("diagnosis_id")
            
            # FIX: Ensure affected_components is never None/Empty if we want a generic estimate
            affected_components = input_data.get("affected_components", [])
            if not affected_components:
                # Fallback to general inspection if no specific components listed
                affected_components = ["DIAGNOSTICS"]

            estimate = await self._cost_service.create_estimate(
                vehicle_id=vehicle_id,
                diagnosis_id=diagnosis_id,
                services_requested=affected_components,
            )

            total = estimate.get("total_estimate", 0)

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "estimate_id": estimate.get("estimate_id"),
                "total_estimate": total,
                "estimate_range": estimate.get("estimate_range"),
                "subtotal_parts": estimate.get("subtotal_parts"),
                "subtotal_labor": estimate.get("subtotal_labor"),
                "warranty_coverage": estimate.get("warranty_coverage"),
                "estimated_labor_hours": estimate.get("estimated_labor_hours"),
                "items": estimate.get("items", []),
                "summary": estimate.get("summary"),
                "confidence_score": estimate.get("confidence_score"),
                "decision": f"Estimated cost: ${total:.2f}",
                "confidence": estimate.get("confidence_score", 0.85),
                "reasoning": f"Cost estimate based on {len(affected_components)} components",
            }

        except Exception as e:
            logger.error(f"Cost estimation failed for {vehicle_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _compare_costs(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare costs between OEM and aftermarket parts"""
        try:
            estimates = await self._cost_service.get_vehicle_estimates(
                vehicle_id=vehicle_id, page=1, page_size=5
            )

            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "estimates": estimates.get("data", []),
                "total_estimates": estimates.get("total", 0),
                "decision": f"Found {estimates.get('total', 0)} estimates for comparison",
                "confidence": 0.90,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_cost_agent: Optional[CostAgent] = None


def get_cost_agent() -> CostAgent:
    global _cost_agent
    if _cost_agent is None:
        _cost_agent = CostAgent()
    return _cost_agent