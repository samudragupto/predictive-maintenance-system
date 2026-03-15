"""
Master Agent - Predictive Maintenance Orchestrator
Coordinates all worker agents and manages the overall workflow
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.agents.base_agent import (
    BaseAgent, AgentType, AgentStatus, AgentAction, AgentMessage,
)
from backend.config.settings import get_settings, RiskLevel
from backend.services.telemetry_service import TelemetryService, get_telemetry_service
from backend.services.vehicle_service import VehicleService, get_vehicle_service
from backend.utils.helpers import generate_reference_number, timestamp_now

settings = get_settings()
logger = logging.getLogger(__name__)


class MasterAgent(BaseAgent):
    """
    Master Orchestrator Agent
    Coordinates the entire predictive maintenance workflow:
    1. Receives telemetry data
    2. Delegates to diagnosis agent
    3. Triggers cost estimation
    4. Schedules service appointments
    5. Monitors driver behavior
    6. Manages feedback loop
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.MASTER,
            version="1.0.0",
        )

        # Worker agents (lazy loaded)
        self._diagnosis_agent = None
        self._cost_agent = None
        self._scheduling_agent = None
        self._behavior_agent = None
        self._feedback_agent = None
        self._ueba_agent = None

        # Services
        self._telemetry_service = get_telemetry_service()
        self._vehicle_service = get_vehicle_service()

        # Workflow tracking
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        self._completed_workflows: List[Dict[str, Any]] = []
        self._max_completed_size: int = 500

        logger.info("MasterAgent initialized - Predictive Maintenance Orchestrator")

    def get_capabilities(self) -> List[str]:
        return [
            "orchestrate_maintenance_workflow",
            "process_telemetry_event",
            "trigger_full_diagnosis",
            "coordinate_service_scheduling",
            "manage_feedback_loop",
            "fleet_health_assessment",
            "agent_coordination",
        ]

    @property
    def diagnosis_agent(self):
        if self._diagnosis_agent is None:
            from backend.agents.diagnosis_agent import get_diagnosis_agent
            self._diagnosis_agent = get_diagnosis_agent()
        return self._diagnosis_agent

    @property
    def cost_agent(self):
        if self._cost_agent is None:
            from backend.agents.cost_agent import get_cost_agent
            self._cost_agent = get_cost_agent()
        return self._cost_agent

    @property
    def scheduling_agent(self):
        if self._scheduling_agent is None:
            from backend.agents.scheduling_agent import get_scheduling_agent
            self._scheduling_agent = get_scheduling_agent()
        return self._scheduling_agent

    @property
    def behavior_agent(self):
        if self._behavior_agent is None:
            from backend.agents.behavior_agent import get_behavior_agent
            self._behavior_agent = get_behavior_agent()
        return self._behavior_agent

    @property
    def feedback_agent(self):
        if self._feedback_agent is None:
            from backend.agents.feedback_agent import get_feedback_agent
            self._feedback_agent = get_feedback_agent()
        return self._feedback_agent

    @property
    def ueba_agent(self):
        if self._ueba_agent is None:
            from backend.agents.ueba_agent import get_ueba_agent
            self._ueba_agent = get_ueba_agent()
        return self._ueba_agent

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing - route to appropriate workflow
        """
        action = input_data.get("action", "process_telemetry")
        vehicle_id = input_data.get("vehicle_id")

        if action == "process_telemetry":
            return await self._handle_telemetry(input_data)
        elif action == "full_diagnosis":
            return await self._handle_full_diagnosis(vehicle_id, input_data)
        elif action == "fleet_assessment":
            return await self._handle_fleet_assessment(input_data)
        elif action == "process_feedback":
            return await self._handle_feedback(input_data)
        elif action == "check_agents_health":
            return await self._check_all_agents_health()
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
            }

    async def orchestrate_maintenance_workflow(
        self, vehicle_id: str, telemetry_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Full predictive maintenance workflow orchestration
        """
        workflow_id = generate_reference_number("WF")
        workflow = {
            "workflow_id": workflow_id,
            "vehicle_id": vehicle_id,
            "started_at": datetime.utcnow().isoformat(),
            "steps": [],
            "status": "IN_PROGRESS",
        }
        self._active_workflows[workflow_id] = workflow

        try:
            logger.info(f"Starting maintenance workflow {workflow_id} for vehicle {vehicle_id}")

            # Step 1: UEBA Security Check
            ueba_result = await self.ueba_agent.execute(
                action_name="monitor_workflow",
                input_data={
                    "vehicle_id": vehicle_id,
                    "workflow_id": workflow_id,
                    "action": "maintenance_workflow",
                },
            )
            workflow["steps"].append({
                "step": 1,
                "agent": "UEBA",
                "action": "security_check",
                "success": ueba_result.success,
                "duration_ms": ueba_result.duration_ms,
            })

            if not ueba_result.success and ueba_result.status == "BLOCKED":
                workflow["status"] = "BLOCKED"
                return {"success": False, "workflow": workflow, "reason": "Security check failed"}

            # Step 2: Diagnosis
            diagnosis_result = await self.diagnosis_agent.execute(
                action_name="diagnose_vehicle",
                input_data={
                    "vehicle_id": vehicle_id,
                    "telemetry_data": telemetry_data,
                },
            )
            workflow["steps"].append({
                "step": 2,
                "agent": "DIAGNOSIS",
                "action": "diagnose_vehicle",
                "success": diagnosis_result.success,
                "duration_ms": diagnosis_result.duration_ms,
                "risk_level": diagnosis_result.output_data.get("risk_level") if diagnosis_result.output_data else None,
            })

            diagnosis_data = diagnosis_result.output_data or {}
            risk_level = diagnosis_data.get("risk_level", "LOW")

            # Step 3: Cost Estimation (if service needed)
            cost_result = None
            if risk_level in ["MEDIUM", "HIGH", "CRITICAL"]:
                cost_result = await self.cost_agent.execute(
                    action_name="estimate_cost",
                    input_data={
                        "vehicle_id": vehicle_id,
                        "diagnosis_id": diagnosis_data.get("diagnosis_id"),
                        "affected_components": diagnosis_data.get("affected_components", []),
                    },
                )
                workflow["steps"].append({
                    "step": 3,
                    "agent": "COST",
                    "action": "estimate_cost",
                    "success": cost_result.success,
                    "duration_ms": cost_result.duration_ms,
                    "total_estimate": cost_result.output_data.get("total_estimate") if cost_result.output_data else None,
                })

            # Step 4: Smart Scheduling (if HIGH or CRITICAL)
            schedule_result = None
            if risk_level in ["HIGH", "CRITICAL"]:
                schedule_result = await self.scheduling_agent.execute(
                    action_name="auto_schedule",
                    input_data={
                        "vehicle_id": vehicle_id,
                        "urgency": risk_level,
                        "diagnosis_id": diagnosis_data.get("diagnosis_id"),
                        "estimated_duration": diagnosis_data.get("estimated_duration_minutes", 90),
                    },
                )
                workflow["steps"].append({
                    "step": 4,
                    "agent": "SCHEDULING",
                    "action": "auto_schedule",
                    "success": schedule_result.success,
                    "duration_ms": schedule_result.duration_ms,
                    "appointment_id": schedule_result.output_data.get("appointment_id") if schedule_result.output_data else None,
                })

            # Step 5: Driver Behavior Analysis
            behavior_result = await self.behavior_agent.execute(
                action_name="analyze_behavior",
                input_data={
                    "vehicle_id": vehicle_id,
                    "telemetry_data": telemetry_data,
                },
            )
            workflow["steps"].append({
                "step": 5,
                "agent": "BEHAVIOR",
                "action": "analyze_behavior",
                "success": behavior_result.success,
                "duration_ms": behavior_result.duration_ms,
                "behavior_score": behavior_result.output_data.get("overall_score") if behavior_result.output_data else None,
            })

            # Complete workflow
            workflow["status"] = "COMPLETED"
            workflow["completed_at"] = datetime.utcnow().isoformat()
            workflow["total_duration_ms"] = sum(
                step.get("duration_ms", 0) for step in workflow["steps"]
            )
            workflow["result"] = {
                "risk_level": risk_level,
                "diagnosis": diagnosis_data,
                "cost_estimate": cost_result.output_data if cost_result else None,
                "appointment": schedule_result.output_data if schedule_result else None,
                "behavior": behavior_result.output_data if behavior_result else None,
                "service_required": risk_level in ["MEDIUM", "HIGH", "CRITICAL"],
                "immediate_attention": risk_level == "CRITICAL",
            }

            # Move to completed
            del self._active_workflows[workflow_id]
            self._completed_workflows.append(workflow)
            if len(self._completed_workflows) > self._max_completed_size:
                self._completed_workflows = self._completed_workflows[-self._max_completed_size:]

            logger.info(
                f"Workflow {workflow_id} completed. Risk: {risk_level}, "
                f"Duration: {workflow['total_duration_ms']}ms"
            )

            return {
                "success": True,
                "workflow": workflow,
                "decision": f"Vehicle requires {'immediate' if risk_level == 'CRITICAL' else 'scheduled' if risk_level in ['MEDIUM', 'HIGH'] else 'no'} service",
                "confidence": diagnosis_data.get("confidence_score", 0.85),
                "reasoning": f"Based on {len(workflow['steps'])} agent analyses",
            }

        except Exception as e:
            workflow["status"] = "FAILED"
            workflow["error"] = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")
            return {
                "success": False,
                "workflow": workflow,
                "error": str(e),
            }

    async def _handle_telemetry(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming telemetry data"""
        vehicle_id = input_data.get("vehicle_id")
        telemetry_data = input_data.get("telemetry_data")

        # Quick risk analysis
        risk_analysis = await self._telemetry_service.get_risk_analysis(vehicle_id)
        risk_level = risk_analysis.get("overall_risk_level", "LOW")

        result = {
            "success": True,
            "vehicle_id": vehicle_id,
            "risk_level": risk_level,
            "health_score": risk_analysis.get("health_score"),
            "decision": "no_action",
            "confidence": risk_analysis.get("confidence_score", 0.8),
        }

        # Trigger full workflow for medium+ risk
        if risk_level in ["MEDIUM", "HIGH", "CRITICAL"]:
            workflow_result = await self.orchestrate_maintenance_workflow(
                vehicle_id, telemetry_data
            )
            result["workflow"] = workflow_result.get("workflow")
            result["decision"] = workflow_result.get("decision")

        return result

    async def _handle_full_diagnosis(
        self, vehicle_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle full diagnosis request"""
        return await self.orchestrate_maintenance_workflow(
            vehicle_id, input_data.get("telemetry_data")
        )

    async def _handle_fleet_assessment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fleet-wide assessment"""
        fleet_overview = await self._vehicle_service.get_fleet_overview(
            input_data.get("fleet_id")
        )
        vehicles_needing_service = await self._vehicle_service.get_vehicles_needing_service()

        return {
            "success": True,
            "fleet_overview": fleet_overview,
            "vehicles_needing_service": vehicles_needing_service,
            "decision": f"{len(vehicles_needing_service)} vehicles require attention",
            "confidence": 0.95,
        }

    async def _handle_feedback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback processing"""
        feedback_result = await self.feedback_agent.execute(
            action_name="process_feedback",
            input_data=input_data,
        )
        return feedback_result.output_data or {"success": False}

    async def _check_all_agents_health(self) -> Dict[str, Any]:
        """Check health of all agents"""
        agents = {
            "master": self,
            "diagnosis": self.diagnosis_agent,
            "cost": self.cost_agent,
            "scheduling": self.scheduling_agent,
            "behavior": self.behavior_agent,
            "feedback": self.feedback_agent,
            "ueba": self.ueba_agent,
        }

        health_checks = {}
        for name, agent in agents.items():
            health_checks[name] = agent.health_check()

        all_healthy = all(h["healthy"] for h in health_checks.values())

        return {
            "success": True,
            "all_healthy": all_healthy,
            "agents": health_checks,
            "decision": "All agents operational" if all_healthy else "Some agents need attention",
            "confidence": 1.0,
        }

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get active workflows"""
        return list(self._active_workflows.values())

    def get_completed_workflows(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get completed workflows"""
        return self._completed_workflows[-limit:]


# Singleton
_master_agent: Optional[MasterAgent] = None


def get_master_agent() -> MasterAgent:
    global _master_agent
    if _master_agent is None:
        _master_agent = MasterAgent()
    return _master_agent