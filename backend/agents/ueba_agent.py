"""
UEBA Agent
User & Entity Behavior Analytics security monitoring
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics

from backend.agents.base_agent import BaseAgent, AgentType, AgentStatus
from backend.services.security_service import SecurityService, get_security_service
from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BehaviorProfile:
    """Behavior profile for an entity"""

    def __init__(self, entity_id: str, entity_type: str):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.action_history: List[Dict[str, Any]] = []
        self.action_counts: Dict[str, int] = defaultdict(int)
        self.avg_processing_times: Dict[str, List[float]] = defaultdict(list)
        self.hourly_activity: Dict[int, int] = defaultdict(int)
        self.error_count: int = 0
        self.total_actions: int = 0
        self.created_at: datetime = datetime.utcnow()
        self.last_activity: Optional[datetime] = None

    def record_action(self, action: Dict[str, Any]) -> None:
        """Record an action to the profile"""
        self.total_actions += 1
        self.last_activity = datetime.utcnow()

        action_name = action.get("action", "unknown")
        self.action_counts[action_name] += 1

        processing_time = action.get("processing_duration_ms", 0)
        if processing_time > 0:
            self.avg_processing_times[action_name].append(processing_time)
            # Keep only last 100 times per action
            if len(self.avg_processing_times[action_name]) > 100:
                self.avg_processing_times[action_name] = (
                    self.avg_processing_times[action_name][-100:]
                )

        if not action.get("success", True):
            self.error_count += 1

        hour = datetime.utcnow().hour
        self.hourly_activity[hour] += 1

        # Keep only last 1000 actions
        self.action_history.append({
            "action": action_name,
            "timestamp": datetime.utcnow().isoformat(),
            "success": action.get("success", True),
            "processing_time": processing_time,
        })
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-1000:]

    def get_baseline(self) -> Dict[str, Any]:
        """Get baseline behavior metrics"""
        avg_times = {}
        for action, times in self.avg_processing_times.items():
            if times:
                avg_times[action] = {
                    "mean": round(statistics.mean(times), 2),
                    "std": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
                    "max": round(max(times), 2),
                    "count": len(times),
                }

        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "total_actions": self.total_actions,
            "error_rate": round(
                self.error_count / self.total_actions * 100, 2
            ) if self.total_actions > 0 else 0,
            "action_distribution": dict(self.action_counts),
            "processing_times": avg_times,
            "peak_hours": sorted(
                self.hourly_activity.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }


class UEBAAgent(BaseAgent):
    """
    UEBA Security Monitor Agent
    Monitors all agent behaviors using User & Entity Behavior Analytics
    Detects anomalies and blocks unauthorized actions
    """

    def __init__(self):
        super().__init__(
            agent_type=AgentType.UEBA,
            version="1.0.0",
        )
        self._security_service = get_security_service()
        self._settings = get_settings()

        # Behavior profiles for each entity
        self._profiles: Dict[str, BehaviorProfile] = {}

        # Thresholds
        self._anomaly_threshold = self._settings.UEBA_ANOMALY_THRESHOLD
        self._blocking_threshold = self._settings.UEBA_BLOCKING_THRESHOLD

        # Rate limiting
        self._rate_limits: Dict[str, List[datetime]] = defaultdict(list)
        self._max_actions_per_minute: int = 60
        self._max_actions_per_hour: int = 1000

        # Blocked entities
        self._blocked_entities: Dict[str, Dict[str, Any]] = {}

        # Alert counters
        self._total_alerts: int = 0
        self._blocked_actions: int = 0

        logger.info("UEBAAgent initialized - Security Monitor Active")

    def get_capabilities(self) -> List[str]:
        return [
            "monitor_workflow",
            "monitor_agent_action",
            "detect_anomalies",
            "rate_limit_check",
            "block_entity",
            "unblock_entity",
            "get_entity_profile",
            "get_security_dashboard",
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process UEBA monitoring request"""
        action = input_data.get("action", "monitor_agent_action")

        if action == "monitor_workflow":
            return await self._monitor_workflow(input_data)
        elif action == "monitor_agent_action":
            return await self._monitor_agent_action(input_data)
        elif action == "check_entity":
            return await self._check_entity(input_data)
        elif action == "get_dashboard":
            return await self._get_security_dashboard()
        elif action == "block_entity":
            return await self._block_entity(input_data)
        elif action == "unblock_entity":
            return await self._unblock_entity(input_data)
        else:
            return await self._monitor_agent_action(input_data)

    async def _monitor_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor a workflow execution"""
        try:
            workflow_id = input_data.get("workflow_id")
            vehicle_id = input_data.get("vehicle_id")
            agent_action = input_data.get("action", "unknown")

            # Check if entity is blocked
            entity_id = input_data.get("agent_id", "system")
            if entity_id in self._blocked_entities:
                self._blocked_actions += 1
                return {
                    "success": False,
                    "blocked": True,
                    "reason": self._blocked_entities[entity_id].get("reason", "Entity blocked"),
                    "decision": "ACTION_BLOCKED",
                    "confidence": 1.0,
                }

            # Rate limit check
            rate_ok = self._check_rate_limit(entity_id)
            if not rate_ok:
                self._blocked_actions += 1
                return {
                    "success": False,
                    "blocked": True,
                    "reason": "Rate limit exceeded",
                    "decision": "RATE_LIMITED",
                    "confidence": 1.0,
                }

            # Record action in profile
            profile = self._get_or_create_profile(entity_id, "AGENT")
            profile.record_action(input_data)

            # Calculate anomaly score
            anomaly_score = self._calculate_anomaly_score(entity_id, input_data)

            # Determine action
            if anomaly_score >= self._blocking_threshold:
                self._blocked_actions += 1
                self._total_alerts += 1

                await self._security_service.log_action({
                    "level": "CRITICAL",
                    "actor_type": "AGENT",
                    "actor_id": entity_id,
                    "action_type": "AGENT_ACTION",
                    "action_name": f"BLOCKED: {agent_action}",
                    "action_description": f"Action blocked due to anomaly score {anomaly_score:.2f}",
                    "success": False,
                })

                return {
                    "success": False,
                    "blocked": True,
                    "anomaly_score": anomaly_score,
                    "reason": f"Anomaly score {anomaly_score:.2f} exceeds blocking threshold",
                    "decision": "ACTION_BLOCKED",
                    "confidence": anomaly_score,
                }

            elif anomaly_score >= self._anomaly_threshold:
                self._total_alerts += 1

                await self._security_service.log_action({
                    "level": "WARNING",
                    "actor_type": "AGENT",
                    "actor_id": entity_id,
                    "action_type": "AGENT_ACTION",
                    "action_name": f"ALERT: {agent_action}",
                    "action_description": f"Anomalous behavior detected: score {anomaly_score:.2f}",
                    "success": True,
                })

                return {
                    "success": True,
                    "blocked": False,
                    "anomaly_score": anomaly_score,
                    "warning": True,
                    "decision": "ACTION_ALLOWED_WITH_WARNING",
                    "confidence": 1 - anomaly_score,
                }

            return {
                "success": True,
                "blocked": False,
                "anomaly_score": anomaly_score,
                "decision": "ACTION_ALLOWED",
                "confidence": 1 - anomaly_score,
            }

        except Exception as e:
            logger.error(f"UEBA monitoring error: {e}")
            # On error, allow action but log
            return {
                "success": True,
                "blocked": False,
                "error": str(e),
                "decision": "ACTION_ALLOWED_ON_ERROR",
                "confidence": 0.5,
            }

    async def _monitor_agent_action(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor a single agent action"""
        return await self._monitor_workflow(input_data)

    async def _check_entity(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check entity status and profile"""
        entity_id = input_data.get("entity_id")
        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        is_blocked = entity_id in self._blocked_entities
        profile = self._profiles.get(entity_id)

        return {
            "success": True,
            "entity_id": entity_id,
            "is_blocked": is_blocked,
            "block_info": self._blocked_entities.get(entity_id) if is_blocked else None,
            "profile": profile.get_baseline() if profile else None,
            "decision": "Entity is blocked" if is_blocked else "Entity is active",
            "confidence": 1.0,
        }

    async def _get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        try:
            alert_summary = await self._security_service.get_alert_summary()
            recent_alerts = await self._security_service.get_ueba_alerts(limit=10)

            return {
                "success": True,
                "alert_summary": alert_summary,
                "recent_alerts": recent_alerts,
                "monitored_entities": len(self._profiles),
                "blocked_entities": len(self._blocked_entities),
                "total_alerts_generated": self._total_alerts,
                "total_blocked_actions": self._blocked_actions,
                "agent_profiles": {
                    eid: profile.get_baseline()
                    for eid, profile in list(self._profiles.items())[:10]
                },
                "decision": "Security dashboard generated",
                "confidence": 1.0,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _block_entity(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Block an entity"""
        entity_id = input_data.get("entity_id")
        reason = input_data.get("reason", "Manual block")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        self._blocked_entities[entity_id] = {
            "reason": reason,
            "blocked_at": datetime.utcnow().isoformat(),
            "blocked_by": input_data.get("blocked_by", "ueba_agent"),
        }

        logger.warning(f"Entity blocked: {entity_id} - {reason}")

        return {
            "success": True,
            "entity_id": entity_id,
            "blocked": True,
            "reason": reason,
            "decision": f"Entity {entity_id} blocked",
            "confidence": 1.0,
        }

    async def _unblock_entity(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unblock an entity"""
        entity_id = input_data.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        if entity_id in self._blocked_entities:
            del self._blocked_entities[entity_id]
            logger.info(f"Entity unblocked: {entity_id}")

        return {
            "success": True,
            "entity_id": entity_id,
            "blocked": False,
            "decision": f"Entity {entity_id} unblocked",
            "confidence": 1.0,
        }

    def _get_or_create_profile(self, entity_id: str, entity_type: str) -> BehaviorProfile:
        """Get or create a behavior profile"""
        if entity_id not in self._profiles:
            self._profiles[entity_id] = BehaviorProfile(entity_id, entity_type)
        return self._profiles[entity_id]

    def _check_rate_limit(self, entity_id: str) -> bool:
        """Check if entity is within rate limits"""
        now = datetime.utcnow()

        # Clean old entries
        self._rate_limits[entity_id] = [
            t for t in self._rate_limits[entity_id]
            if (now - t).total_seconds() < 3600
        ]

        # Add current action
        self._rate_limits[entity_id].append(now)

        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        recent_count = sum(
            1 for t in self._rate_limits[entity_id]
            if t > one_minute_ago
        )

        if recent_count > self._max_actions_per_minute:
            logger.warning(f"Rate limit exceeded for {entity_id}: {recent_count}/min")
            return False

        # Check per-hour limit
        if len(self._rate_limits[entity_id]) > self._max_actions_per_hour:
            logger.warning(f"Hourly rate limit exceeded for {entity_id}")
            return False

        return True

    def _calculate_anomaly_score(
        self, entity_id: str, action_data: Dict[str, Any]
    ) -> float:
        """Calculate anomaly score for an action"""
        score = 0.0
        profile = self._profiles.get(entity_id)

        if not profile or profile.total_actions < 10:
            return 0.1  # Low score for new entities

        baseline = profile.get_baseline()

        # Check error rate
        error_rate = baseline.get("error_rate", 0)
        if error_rate > 50:
            score += 0.3
        elif error_rate > 25:
            score += 0.15

        # Check processing time deviation
        action_name = action_data.get("action", "unknown")
        processing_time = action_data.get("processing_duration_ms", 0)

        if action_name in profile.avg_processing_times:
            times = profile.avg_processing_times[action_name]
            if len(times) >= 5:
                mean_time = statistics.mean(times)
                std_time = statistics.stdev(times) if len(times) > 1 else mean_time * 0.5

                if std_time > 0 and processing_time > 0:
                    z_score = abs(processing_time - mean_time) / std_time
                    if z_score > 3:
                        score += 0.25
                    elif z_score > 2:
                        score += 0.1

        # Check for unusual hour
        current_hour = datetime.utcnow().hour
        if profile.hourly_activity:
            total_activity = sum(profile.hourly_activity.values())
            hour_ratio = profile.hourly_activity.get(current_hour, 0) / total_activity if total_activity > 0 else 0
            if hour_ratio < 0.01 and profile.total_actions > 100:
                score += 0.15  # Unusual time of activity

        # Check for rapid succession
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_actions = sum(
            1 for t in self._rate_limits.get(entity_id, [])
            if t > one_minute_ago
        )
        if recent_actions > 30:
            score += 0.2

        return min(score, 1.0)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get overall monitoring statistics"""
        return {
            "monitored_entities": len(self._profiles),
            "blocked_entities": len(self._blocked_entities),
            "total_alerts": self._total_alerts,
            "blocked_actions": self._blocked_actions,
            "anomaly_threshold": self._anomaly_threshold,
            "blocking_threshold": self._blocking_threshold,
        }


# Singleton
_ueba_agent: Optional[UEBAAgent] = None


def get_ueba_agent() -> UEBAAgent:
    global _ueba_agent
    if _ueba_agent is None:
        _ueba_agent = UEBAAgent()
    return _ueba_agent