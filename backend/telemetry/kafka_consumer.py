"""
Kafka Consumer for Telemetry
Consumes telemetry data from Kafka topics for processing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass
import uuid

from backend.config.settings import get_settings
from backend.telemetry.processor import TelemetryProcessor, get_processor

settings = get_settings()
logger = logging.getLogger(__name__)

# Try to import aiokafka, provide fallback if not available
try:
    from aiokafka import AIOKafkaConsumer
    from aiokafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("aiokafka not installed. Kafka consumer will use mock mode.")


@dataclass
class ConsumerConfig:
    """Kafka consumer configuration"""
    bootstrap_servers: str
    group_id: str = "predictive-maintenance-consumer"
    client_id: str = "predictive-maintenance-consumer"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    max_poll_records: int = 500
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


class MockKafkaConsumer:
    """Mock Kafka consumer for development/testing"""
    
    def __init__(self, *topics):
        self._topics = topics
        self._messages: asyncio.Queue = asyncio.Queue()
        self._is_running: bool = False
        logger.info(f"MockKafkaConsumer initialized for topics: {topics}")
    
    async def start(self):
        self._is_running = True
        logger.info("MockKafkaConsumer started")
    
    async def stop(self):
        self._is_running = False
        logger.info("MockKafkaConsumer stopped")
    
    async def getmany(self, timeout_ms: int = 1000):
        """Get messages from queue"""
        messages = {}
        try:
            # Try to get messages with timeout
            while not self._messages.empty():
                msg = await asyncio.wait_for(
                    self._messages.get(),
                    timeout=timeout_ms / 1000
                )
                topic = msg.get("topic", "unknown")
                if topic not in messages:
                    messages[topic] = []
                messages[topic].append(msg)
        except asyncio.TimeoutError:
            pass
        return messages
    
    async def add_message(self, message: Dict[str, Any]):
        """Add a message to the queue (for testing)"""
        await self._messages.put(message)
    
    def subscribe(self, topics: List[str]):
        self._topics = topics


class TelemetryKafkaConsumer:
    """
    Kafka consumer for telemetry data
    Consumes and processes telemetry messages
    """
    
    def __init__(self, config: Optional[ConsumerConfig] = None):
        self.settings = get_settings()
        self.config = config or ConsumerConfig(
            bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS
        )
        
        self._consumer: Optional[Any] = None
        self._is_connected: bool = False
        self._is_consuming: bool = False
        self._message_count: int = 0
        self._error_count: int = 0
        self._consume_task: Optional[asyncio.Task] = None
        
        # Processors
        self._telemetry_processor: TelemetryProcessor = get_processor()
        self._message_handlers: Dict[str, List[Callable]] = {}
        
        # Topics
        self.topics = [
            self.settings.KAFKA_TELEMETRY_TOPIC,
            self.settings.KAFKA_ALERTS_TOPIC,
        ]
        
        logger.info(f"TelemetryKafkaConsumer initialized for {self.config.bootstrap_servers}")
    
    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a message handler for a specific topic"""
        if topic not in self._message_handlers:
            self._message_handlers[topic] = []
        self._message_handlers[topic].append(handler)
        logger.info(f"Registered handler for topic: {topic}")
    
    async def connect(self) -> bool:
        """Connect to Kafka cluster"""
        if self._is_connected:
            logger.warning("Consumer already connected")
            return True
        
        try:
            if KAFKA_AVAILABLE:
                self._consumer = AIOKafkaConsumer(
                    *self.topics,
                    bootstrap_servers=self.config.bootstrap_servers,
                    group_id=self.config.group_id,
                    client_id=self.config.client_id,
                    auto_offset_reset=self.config.auto_offset_reset,
                    enable_auto_commit=self.config.enable_auto_commit,
                    auto_commit_interval_ms=self.config.auto_commit_interval_ms,
                    max_poll_records=self.config.max_poll_records,
                    session_timeout_ms=self.config.session_timeout_ms,
                    heartbeat_interval_ms=self.config.heartbeat_interval_ms,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                )
                await self._consumer.start()
            else:
                self._consumer = MockKafkaConsumer(*self.topics)
                await self._consumer.start()
            
            self._is_connected = True
            logger.info("Kafka consumer connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Kafka consumer: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster"""
        self._is_consuming = False
        
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
        
        if self._consumer:
            try:
                await self._consumer.stop()
                logger.info("Kafka consumer disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Kafka consumer: {e}")
            finally:
                self._consumer = None
                self._is_connected = False
    
    async def start_consuming(self) -> None:
        """Start consuming messages"""
        if not self._is_connected:
            if not await self.connect():
                logger.error("Cannot start consuming: not connected")
                return
        
        self._is_consuming = True
        logger.info("Starting to consume messages")
        
        try:
            if KAFKA_AVAILABLE:
                async for message in self._consumer:
                    if not self._is_consuming:
                        break
                    await self._process_message(message)
            else:
                # Mock mode: poll for messages
                while self._is_consuming:
                    messages = await self._consumer.getmany(timeout_ms=1000)
                    for topic, topic_messages in messages.items():
                        for msg in topic_messages:
                            await self._process_message(msg)
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info("Consuming cancelled")
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
        finally:
            self._is_consuming = False
    
    async def start_consuming_background(self) -> None:
        """Start consuming in background task"""
        self._consume_task = asyncio.create_task(self.start_consuming())
        logger.info("Started background consumer task")
    
    def stop_consuming(self) -> None:
        """Stop consuming messages"""
        self._is_consuming = False
        logger.info("Stop consuming requested")
    
    async def _process_message(self, message: Any) -> None:
        """Process a single Kafka message"""
        try:
            # Extract message data
            if KAFKA_AVAILABLE:
                topic = message.topic
                key = message.key
                value = message.value
                timestamp = datetime.fromtimestamp(message.timestamp / 1000) if message.timestamp else datetime.utcnow()
            else:
                # Mock message format
                topic = message.get("topic", "unknown")
                key = message.get("key")
                value = message.get("value", message)
                timestamp = datetime.fromisoformat(message.get("timestamp", datetime.utcnow().isoformat()))
            
            logger.debug(f"Processing message from topic {topic}, key={key}")
            
            # Handle based on topic
            if topic == self.settings.KAFKA_TELEMETRY_TOPIC:
                await self._handle_telemetry_message(value)
            elif topic == self.settings.KAFKA_ALERTS_TOPIC:
                await self._handle_alert_message(value)
            
            # Call registered handlers
            if topic in self._message_handlers:
                for handler in self._message_handlers[topic]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(value)
                        else:
                            handler(value)
                    except Exception as e:
                        logger.error(f"Handler error for topic {topic}: {e}")
            
            self._message_count += 1
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error processing message: {e}")
    
    async def _handle_telemetry_message(self, data: Dict[str, Any]) -> None:
        """Handle telemetry message"""
        try:
            result = await self._telemetry_processor.process_telemetry(data)
            
            if not result.get("success"):
                logger.warning(f"Telemetry processing failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Error handling telemetry message: {e}")
    
    async def _handle_alert_message(self, data: Dict[str, Any]) -> None:
        """Handle alert message"""
        try:
            alert_id = data.get("alert_id", "unknown")
            vehicle_id = data.get("vehicle_id", "unknown")
            risk_level = data.get("risk_level", "UNKNOWN")
            
            logger.warning(f"Alert received: {alert_id} for vehicle {vehicle_id}, level={risk_level}")
            
            # TODO: Implement alert handling (notifications, escalation, etc.)
            
        except Exception as e:
            logger.error(f"Error handling alert message: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            "is_connected": self._is_connected,
            "is_consuming": self._is_consuming,
            "message_count": self._message_count,
            "error_count": self._error_count,
            "success_rate": (
                self._message_count / (self._message_count + self._error_count)
                if (self._message_count + self._error_count) > 0
                else 1.0
            ),
        }
    
    async def health_check(self) -> bool:
        """Check consumer health"""
        return self._is_connected and self._is_consuming


# Singleton instance
_consumer_instance: Optional[TelemetryKafkaConsumer] = None


async def get_kafka_consumer() -> TelemetryKafkaConsumer:
    """Get or create Kafka consumer instance"""
    global _consumer_instance
    if _consumer_instance is None:
        _consumer_instance = TelemetryKafkaConsumer()
    return _consumer_instance