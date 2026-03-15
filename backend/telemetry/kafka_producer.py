"""
Kafka Producer for Telemetry
Publishes telemetry data to Kafka topics for real-time processing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import uuid

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Try to import aiokafka, provide fallback if not available
try:
    from aiokafka import AIOKafkaProducer
    from aiokafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("aiokafka not installed. Kafka producer will use mock mode.")


@dataclass
class ProducerConfig:
    """Kafka producer configuration"""
    bootstrap_servers: str
    client_id: str = "predictive-maintenance-producer"
    acks: str = "all"
    retries: int = 3
    retry_backoff_ms: int = 100
    compression_type: str = "gzip"
    batch_size: int = 16384
    linger_ms: int = 10
    buffer_memory: int = 33554432  # 32 MB
    max_request_size: int = 1048576  # 1 MB


class MockKafkaProducer:
    """Mock Kafka producer for development/testing"""
    
    def __init__(self):
        self._messages: List[Dict[str, Any]] = []
        self._callbacks: List[Callable] = []
        logger.info("MockKafkaProducer initialized (Kafka not available)")
    
    async def start(self):
        logger.info("MockKafkaProducer started")
    
    async def stop(self):
        logger.info("MockKafkaProducer stopped")
    
    async def send_and_wait(self, topic: str, value: bytes, key: Optional[bytes] = None):
        message = {
            "topic": topic,
            "key": key.decode() if key else None,
            "value": json.loads(value.decode()),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._messages.append(message)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        logger.debug(f"MockKafka: Sent message to topic {topic}")
        return message
    
    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages.copy()
    
    def clear_messages(self):
        self._messages.clear()


class TelemetryKafkaProducer:
    """
    Kafka producer for telemetry data
    Handles message serialization and delivery
    """
    
    def __init__(self, config: Optional[ProducerConfig] = None):
        self.settings = get_settings()
        self.config = config or ProducerConfig(
            bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS
        )
        
        self._producer: Optional[Any] = None
        self._is_connected: bool = False
        self._message_count: int = 0
        self._error_count: int = 0
        
        # Topics
        self.telemetry_topic = self.settings.KAFKA_TELEMETRY_TOPIC
        self.alerts_topic = self.settings.KAFKA_ALERTS_TOPIC
        
        logger.info(f"TelemetryKafkaProducer initialized for {self.config.bootstrap_servers}")
    
    async def connect(self) -> bool:
        """Connect to Kafka cluster"""
        if self._is_connected:
            logger.warning("Producer already connected")
            return True
        
        try:
            if KAFKA_AVAILABLE:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.config.bootstrap_servers,
                    client_id=self.config.client_id,
                    acks=self.config.acks,
                    compression_type=self.config.compression_type,
                    max_batch_size=self.config.batch_size,
                    linger_ms=self.config.linger_ms,
                    max_request_size=self.config.max_request_size,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                )
                await self._producer.start()
            else:
                self._producer = MockKafkaProducer()
                await self._producer.start()
            
            self._is_connected = True
            logger.info("Kafka producer connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Kafka producer: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster"""
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka producer disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Kafka producer: {e}")
            finally:
                self._producer = None
                self._is_connected = False
    
    async def send_telemetry(self, telemetry: Dict[str, Any]) -> bool:
        """
        Send telemetry data to Kafka
        """
        if not self._is_connected:
            if not await self.connect():
                logger.error("Cannot send telemetry: not connected")
                return False
        
        try:
            vehicle_id = telemetry.get("vehicle_id", "unknown")
            
            # Add metadata
            message = {
                **telemetry,
                "message_id": str(uuid.uuid4()),
                "produced_at": datetime.utcnow().isoformat(),
            }
            
            # Send to Kafka
            if KAFKA_AVAILABLE:
                await self._producer.send_and_wait(
                    topic=self.telemetry_topic,
                    key=vehicle_id,
                    value=message,
                )
            else:
                await self._producer.send_and_wait(
                    topic=self.telemetry_topic,
                    value=json.dumps(message).encode(),
                    key=vehicle_id.encode(),
                )
            
            self._message_count += 1
            logger.debug(f"Sent telemetry for vehicle {vehicle_id} to Kafka")
            return True
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error sending telemetry to Kafka: {e}")
            return False
    
    async def send_batch(self, telemetry_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send a batch of telemetry data to Kafka
        """
        if not self._is_connected:
            if not await self.connect():
                return {"success": False, "error": "Not connected", "sent": 0, "failed": len(telemetry_batch)}
        
        sent = 0
        failed = 0
        
        for telemetry in telemetry_batch:
            if await self.send_telemetry(telemetry):
                sent += 1
            else:
                failed += 1
        
        logger.info(f"Batch send complete: {sent} sent, {failed} failed")
        return {
            "success": failed == 0,
            "sent": sent,
            "failed": failed,
            "total": len(telemetry_batch),
        }
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send alert to alerts topic
        """
        if not self._is_connected:
            if not await self.connect():
                logger.error("Cannot send alert: not connected")
                return False
        
        try:
            vehicle_id = alert.get("vehicle_id", "unknown")
            
            message = {
                **alert,
                "message_id": str(uuid.uuid4()),
                "produced_at": datetime.utcnow().isoformat(),
            }
            
            if KAFKA_AVAILABLE:
                await self._producer.send_and_wait(
                    topic=self.alerts_topic,
                    key=vehicle_id,
                    value=message,
                )
            else:
                await self._producer.send_and_wait(
                    topic=self.alerts_topic,
                    value=json.dumps(message).encode(),
                    key=vehicle_id.encode(),
                )
            
            logger.info(f"Sent alert for vehicle {vehicle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending alert to Kafka: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics"""
        return {
            "is_connected": self._is_connected,
            "message_count": self._message_count,
            "error_count": self._error_count,
            "success_rate": (
                self._message_count / (self._message_count + self._error_count)
                if (self._message_count + self._error_count) > 0
                else 1.0
            ),
        }
    
    async def health_check(self) -> bool:
        """Check producer health"""
        return self._is_connected


# Singleton instance
_producer_instance: Optional[TelemetryKafkaProducer] = None


async def get_kafka_producer() -> TelemetryKafkaProducer:
    """Get or create Kafka producer instance"""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = TelemetryKafkaProducer()
        await _producer_instance.connect()
    return _producer_instance