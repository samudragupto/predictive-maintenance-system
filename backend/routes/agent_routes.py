"""
Agent Routes
API endpoints for AI agent management and interaction
"""

from fastapi import APIRouter, Query, Path, HTTPException, Depends, Body
from typing import Optional, Dict, Any
import logging

from backend.agents.master_agent import MasterAgent, get_master_agent
from backend.agents.diagnosis_agent import get_diagnosis_agent
from backend.agents.cost_agent import get_cost_agent
from backend.agents.scheduling_agent import get_scheduling_agent
from backend.agents.behavior_agent import get_behavior_agent
from backend.agents.feedback_agent import get_feedback_agent
from backend.agents.ueba_agent import get_ueba_agent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/orchestrate", response_model=None, status_code=201)
async def orchestrate_workflow(
    vehicle_id: str = Query(..., description="Vehicle ID"),
    telemetry_data: Optional[Dict[str, Any]] = Body(None),
):
    """Trigger full maintenance workflow orchestration"""
    try:
        master = get_master_agent()
        result = await master.orchestrate_maintenance_workflow(
            vehicle_id=vehicle_id,
            telemetry_data=telemetry_data,
        )
        return result
    except Exception as e:
        logger.error(f"Error orchestrating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=None, status_code=201)
async def execute_agent_action(
    agent_type: str = Query(..., description="Agent type"),
    action: str = Query(..., description="Action name"),
    input_data: Dict[str, Any] = Body({}),
):
    """Execute a specific agent action"""
    try:
        agent_map = {
            "master": get_master_agent,
            "diagnosis": get_diagnosis_agent,
            "cost": get_cost_agent,
            "scheduling": get_scheduling_agent,
            "behavior": get_behavior_agent,
            "feedback": get_feedback_agent,
            "ueba": get_ueba_agent,
        }

        agent_factory = agent_map.get(agent_type.lower())
        if not agent_factory:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent type: {agent_type}. Available: {list(agent_map.keys())}",
            )

        agent = agent_factory()
        input_data["action"] = action
        result = await agent.execute(
            action_name=action,
            input_data=input_data,
        )

        return {
            "success": result.success,
            "action_id": result.action_id,
            "agent_type": result.agent_type,
            "action": result.action_name,
            "duration_ms": result.duration_ms,
            "status": result.status,
            "result": result.output_data,
            "confidence": result.confidence,
            "decision": result.decision,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing agent action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=None)
async def check_agents_health():
    """Check health of all AI agents"""
    try:
        master = get_master_agent()
        result = await master.execute(
            action_name="check_agents_health",
            input_data={"action": "check_agents_health"},
        )
        return result.output_data
    except Exception as e:
        logger.error(f"Error checking agent health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=None)
async def get_agent_stats():
    """Get statistics for all agents"""
    try:
        agents = {
            "master": get_master_agent(),
            "diagnosis": get_diagnosis_agent(),
            "cost": get_cost_agent(),
            "scheduling": get_scheduling_agent(),
            "behavior": get_behavior_agent(),
            "feedback": get_feedback_agent(),
            "ueba": get_ueba_agent(),
        }

        stats = {}
        for name, agent in agents.items():
            stats[name] = agent.get_stats()

        return {"success": True, "agents": stats}
    except Exception as e:
        logger.error(f"Error getting agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{agent_type}", response_model=None)
async def get_single_agent_stats(
    agent_type: str = Path(..., description="Agent type"),
):
    """Get statistics for a specific agent"""
    try:
        agent_map = {
            "master": get_master_agent,
            "diagnosis": get_diagnosis_agent,
            "cost": get_cost_agent,
            "scheduling": get_scheduling_agent,
            "behavior": get_behavior_agent,
            "feedback": get_feedback_agent,
            "ueba": get_ueba_agent,
        }

        agent_factory = agent_map.get(agent_type.lower())
        if not agent_factory:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_type}")

        agent = agent_factory()
        return {"success": True, "data": agent.get_stats()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{agent_type}", response_model=None)
async def get_agent_history(
    agent_type: str = Path(..., description="Agent type"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent action history for an agent"""
    try:
        agent_map = {
            "master": get_master_agent,
            "diagnosis": get_diagnosis_agent,
            "cost": get_cost_agent,
            "scheduling": get_scheduling_agent,
            "behavior": get_behavior_agent,
            "feedback": get_feedback_agent,
            "ueba": get_ueba_agent,
        }

        agent_factory = agent_map.get(agent_type.lower())
        if not agent_factory:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_type}")

        agent = agent_factory()
        history = agent.get_action_history(limit)
        return {"success": True, "data": history, "count": len(history)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/active", response_model=None)
async def get_active_workflows():
    """Get active workflows"""
    try:
        master = get_master_agent()
        workflows = master.get_active_workflows()
        return {"success": True, "data": workflows, "count": len(workflows)}
    except Exception as e:
        logger.error(f"Error getting active workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/completed", response_model=None)
async def get_completed_workflows(
    limit: int = Query(20, ge=1, le=100),
):
    """Get completed workflows"""
    try:
        master = get_master_agent()
        workflows = master.get_completed_workflows(limit)
        return {"success": True, "data": workflows, "count": len(workflows)}
    except Exception as e:
        logger.error(f"Error getting completed workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))