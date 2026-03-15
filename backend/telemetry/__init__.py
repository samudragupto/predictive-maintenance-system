"""
Telemetry Module
Handles vehicle telemetry simulation, collection, and processing
"""

from .simulator import TelemetrySimulator, VehicleSimulationProfile
from .processor import TelemetryProcessor, RiskAnalyzer
from .kafka_producer import TelemetryKafkaProducer
from .kafka_consumer import TelemetryKafkaConsumer
from .aggregator import TelemetryAggregator

__all__ = [
    "TelemetrySimulator",
    "VehicleSimulationProfile",
    "TelemetryProcessor",
    "RiskAnalyzer",
    "TelemetryKafkaProducer",
    "TelemetryKafkaConsumer",
    "TelemetryAggregator",
]