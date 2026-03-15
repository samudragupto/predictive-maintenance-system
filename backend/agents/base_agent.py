"""
Base Agent
Abstract base class for all AI agents in the system
"""

import asyncio
import logging
import uuid
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from backend.config.settings import get_settings
from backend.services.security_service import SecurityService, get_security_service
from backend.utils.helpers import generate_reference_number, timestamp_now

settings = get_settings()
logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent operational status"""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"
    MAINTENANCE = "MAINTENANCE"


class AgentType(str, Enum):
    """Types of agents in the system"""
    MASTER = "MASTER_AGENT"
    DIAGNOSIS = "DIAGNOSIS_AGENT"
    COST = "COST_AGENT"
    SCHEDULING = "SCHEDULING_AGENT"
    BEHAVIOR = "BEHAVIOR_AGENT"
    FEEDBACK = "FEEDBACK_AGENT"
    UEBA = "UEBA_AGENT"


@dataclass
class AgentAction:
    """Represents an action performed by an agent"""
    action_id: str
    agent_type: str
    agent_id: str
    action_name: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    status: str = "PENDING"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    success: bool = False
    error_message: Optional[str] = None
    confidence: Optional[float] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message passed between agents"""
    message_id: str
    sender: str
    receiver: str
    message_type: str  # REQUEST, RESPONSE, NOTIFICATION, ALERT
    subject: str
    payload: Dict[str, Any]
    priority: int = 5  # 1 (highest) to 10 (lowest)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    requires_response: bool = False
    ttl_seconds: int = 300  # Time to live


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents
    Provides common functionality for logging, security, and communication
    """

    def __init__(
        self,
        agent_type: AgentType,
        agent_id: Optional[str] = None,
        version: str = "1.0.0",
    ):
        self.agent_type = agent_type
        self.agent_id = agent_id or f"{agent_type.value}-{uuid.uuid4().hex[:8]}"
        self.version = version
        self.status = AgentStatus.IDLE
        self.settings = get_settings()

        # Performance metrics
        self._action_count: int = 0
        self._success_count: int = 0
        self._error_count: int = 0
        self._total_processing_time_ms: int = 0
        self._created_at: datetime = datetime.utcnow()
        self._last_action_at: Optional[datetime] = None

        # Message inbox
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._message_handlers: Dict[str, Callable] = {}

        # Security service reference
        self._security_service: Optional[SecurityService] = None

        # Action history
        self._action_history: List[AgentAction] = []
        self._max_history_size: int = 100

        logger.info(
            f"Agent initialized: {self.agent_type.value} (ID: {self.agent_id}, v{self.version})"
        )

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method - must be implemented by each agent
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Return list of capabilities this agent provides
        """
        pass

    async def execute(
        self,
        action_name: str,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> AgentAction:
        """
        Execute an action with full logging and monitoring
        """
        action = AgentAction(
            action_id=generate_reference_number("ACT"),
            agent_type=self.agent_type.value,
            agent_id=self.agent_id,
            action_name=action_name,
            input_data=input_data,
            started_at=datetime.utcnow(),
            status="PROCESSING",
        )

        self.status = AgentStatus.PROCESSING
        start_time = time.perf_counter()

        try:
            # Check with UEBA before executing
            security_check = await self._security_check(action_name, input_data)
            if security_check.get("blocked"):
                action.status = "BLOCKED"
                action.success = False
                action.error_message = security_check.get("reason", "Action blocked by UEBA")
                self.status = AgentStatus.BLOCKED
                logger.warning(
                    f"Agent {self.agent_id} action '{action_name}' BLOCKED by UEBA"
                )
                return action

            # Execute the main processing
            result = await self.process(input_data)

            # Update action with results
            action.output_data = result
            action.success = result.get("success", True)
            action.confidence = result.get("confidence")
            action.decision = result.get("decision")
            action.reasoning = result.get("reasoning")
            action.status = "COMPLETED"

            self._success_count += 1

        except Exception as e:
            action.success = False
            action.error_message = str(e)
            action.status = "FAILED"
            self._error_count += 1
            logger.error(
                f"Agent {self.agent_id} action '{action_name}' FAILED: {e}"
            )

        finally:
            # Calculate duration
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            action.duration_ms = elapsed_ms
            action.completed_at = datetime.utcnow()

            self._action_count += 1
            self._total_processing_time_ms += elapsed_ms
            self._last_action_at = datetime.utcnow()
            self.status = AgentStatus.IDLE

            # Store action in history
            self._add_to_history(action)

            # Log agent action to security service
            await self._log_action(action, correlation_id)

        return action

    async def _security_check(
        self, action_name: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check with UEBA security before executing action"""
        if not self.settings.UEBA_ENABLED:
            return {"blocked": False}

        try:
            # Simple security checks
            # In production, this would call the UEBA agent
            return {"blocked": False}
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return {"blocked": False}

    async def _log_action(
        self, action: AgentAction, correlation_id: Optional[str] = None
    ) -> None:
        """Log action to security service"""
        try:
            if self._security_service is None:
                self._security_service = get_security_service()

            await self._security_service.log_agent_action({
                "agent_type": action.agent_type,
                "agent_id": action.agent_id,
                "agent_version": self.version,
                "action": action.action_name,
                "action_category": "AGENT_ACTION",
                "input_summary": str(action.input_data)[:500] if action.input_data else None,
                "processing_duration_ms": action.duration_ms,
                "output_summary": str(action.output_data)[:500] if action.output_data else None,
                "decision_made": action.decision,
                "decision_confidence": action.confidence,
                "decision_reasoning": action.reasoning,
                "success": action.success,
                "error_message": action.error_message,
                "affected_vehicle_id": action.input_data.get("vehicle_id") if action.input_data else None,
                "correlation_id": correlation_id,
            })
        except Exception as e:
            logger.error(f"Failed to log agent action: {e}")

    def _add_to_history(self, action: AgentAction) -> None:
        """Add action to history with size limit"""
        self._action_history.append(action)
        if len(self._action_history) > self._max_history_size:
            self._action_history = self._action_history[-self._max_history_size:]

    async def send_message(
        self, receiver: str, subject: str, payload: Dict[str, Any],
        message_type: str = "REQUEST", priority: int = 5,
        correlation_id: Optional[str] = None,
    ) -> AgentMessage:
        """Send a message to another agent"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            subject=subject,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        logger.debug(f"Agent {self.agent_id} sending message to {receiver}: {subject}")
        return message

    async def receive_message(self, message: AgentMessage) -> None:
        """Receive a message from another agent"""
        await self._inbox.put(message)
        logger.debug(f"Agent {self.agent_id} received message from {message.sender}: {message.subject}")

    async def process_inbox(self) -> None:
        """Process all messages in the inbox"""
        while not self._inbox.empty():
            message = await self._inbox.get()
            handler = self._message_handlers.get(message.subject)
            if handler:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error processing message {message.message_id}: {e}")

    def register_message_handler(self, subject: str, handler: Callable) -> None:
        """Register a handler for a message subject"""
        self._message_handlers[subject] = handler

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        avg_processing_time = (
            self._total_processing_time_ms / self._action_count
            if self._action_count > 0
            else 0
        )

        return {
            "agent_type": self.agent_type.value,
            "agent_id": self.agent_id,
            "version": self.version,
            "status": self.status.value,
            "created_at": self._created_at.isoformat(),
            "last_action_at": self._last_action_at.isoformat() if self._last_action_at else None,
            "metrics": {
                "total_actions": self._action_count,
                "successful_actions": self._success_count,
                "failed_actions": self._error_count,
                "success_rate": round(
                    self._success_count / self._action_count * 100, 2
                ) if self._action_count > 0 else 100.0,
                "total_processing_time_ms": self._total_processing_time_ms,
                "average_processing_time_ms": round(avg_processing_time, 2),
            },
            "capabilities": self.get_capabilities(),
        }

    def get_action_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent action history"""
        recent = self._action_history[-limit:]
        return [
            {
                "action_id": a.action_id,
                "action_name": a.action_name,
                "status": a.status,
                "success": a.success,
                "duration_ms": a.duration_ms,
                "confidence": a.confidence,
                "decision": a.decision,
                "started_at": a.started_at.isoformat() if a.started_at else None,
            }
            for a in reversed(recent)
        ]

    def health_check(self) -> Dict[str, Any]:
        """Check agent health"""
        is_healthy = self.status not in [AgentStatus.ERROR, AgentStatus.BLOCKED]
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "healthy": is_healthy,
            "status": self.status.value,
            "uptime_seconds": int((datetime.utcnow() - self._created_at).total_seconds()),
        }

    def __repr__(self) -> str:
        return f"<{self.agent_type.value}(id={self.agent_id}, status={self.status.value})>"