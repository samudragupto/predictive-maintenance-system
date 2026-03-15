"""
Telemetry Processor
Processes incoming telemetry data, performs risk analysis, and triggers alerts
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import joblib
import pandas as pd
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.config.settings import get_settings, RiskLevel
from backend.models import TelemetryData, TelemetrySnapshot, Vehicle, Diagnosis
from backend.models import get_async_db_context

settings = get_settings()
logger = logging.getLogger(__name__)


class AlertPriority(str, Enum):
    """Alert priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskIndicator:
    """Single risk indicator"""
    component: str
    metric_name: str
    current_value: float
    threshold_warning: float
    threshold_critical: float
    risk_level: str
    message: str
    confidence: float = 1.0


@dataclass
class RiskAssessment:
    """Overall risk assessment result"""
    vehicle_id: str
    timestamp: datetime
    overall_risk_level: str
    health_score: float
    risk_indicators: List[RiskIndicator]
    requires_immediate_attention: bool
    recommended_actions: List[str]
    confidence_score: float


class RiskAnalyzer:
    """
    Analyzes telemetry data to determine risk levels using ML and Rules
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.model_path = "backend/ml_models/failure_prediction_model.pkl"
        self.model = None
        self._load_model()
        
        # Rule-based thresholds (Fallback & Detail generation)
        self.thresholds = {
            "engine_temperature": {
                "warning": self.settings.ENGINE_TEMP_WARNING,
                "critical": self.settings.ENGINE_TEMP_CRITICAL,
                "unit": "°C",
            },
            "battery_voltage": {
                "warning": self.settings.BATTERY_VOLTAGE_LOW,
                "critical": self.settings.BATTERY_VOLTAGE_CRITICAL,
                "unit": "V",
                "inverse": True,
            },
            "oil_level": {
                "warning": self.settings.OIL_LEVEL_LOW,
                "critical": self.settings.OIL_LEVEL_CRITICAL,
                "unit": "%",
                "inverse": True,
            },
            "brake_wear": {
                "warning": self.settings.BRAKE_WEAR_WARNING,
                "critical": self.settings.BRAKE_WEAR_CRITICAL,
                "unit": "%",
            },
            "tire_pressure": {
                "warning": self.settings.TIRE_PRESSURE_LOW,
                "critical": self.settings.TIRE_PRESSURE_CRITICAL,
                "unit": "PSI",
                "inverse": True,
            },
        }
        
        self.component_weights = {
            "engine": 0.25,
            "battery": 0.15,
            "oil": 0.15,
            "brakes": 0.20,
            "tires": 0.10,
            "fuel": 0.05,
            "transmission": 0.10,
        }
        
        logger.info("RiskAnalyzer initialized")

    def _load_model(self):
        """Load the ML model if available"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("🧠 ML Model loaded successfully")
            else:
                logger.warning("⚠️ ML Model not found. Using fallback rules.")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
    
    def analyze(self, telemetry: Dict[str, Any]) -> RiskAssessment:
        """
        Perform comprehensive risk analysis on telemetry data
        """
        vehicle_id = telemetry.get("vehicle_id", "UNKNOWN")
        timestamp = datetime.fromisoformat(telemetry.get("timestamp", datetime.utcnow().isoformat()))
        
        # --- ML PREDICTION ---
        ml_risk_level = "LOW"
        ml_confidence = 1.0
        
        if self.model:
            try:
                features = pd.DataFrame([{
                    'engine_temp': telemetry.get('engine_temperature_celsius', 90),
                    'rpm': telemetry.get('engine_rpm', 2000),
                    'battery': telemetry.get('battery_voltage', 12.6),
                    'oil': telemetry.get('oil_level_percent', 80),
                    'vibration': telemetry.get('vibration_level', 2.0)
                }])
                
                prediction = self.model.predict(features)[0] # 0, 1, 2
                probs = self.model.predict_proba(features)[0]
                ml_confidence = max(probs)
                
                if prediction == 2:
                    ml_risk_level = "CRITICAL"
                elif prediction == 1:
                    ml_risk_level = "HIGH"
                else:
                    ml_risk_level = "LOW"
            except Exception as e:
                logger.error(f"ML Prediction failed: {e}")

        # --- RULE BASED ANALYSIS (For Details) ---
        risk_indicators = []
        component_scores = {}
        
        # Analyze each component
        engine_risks = self._analyze_engine(telemetry)
        risk_indicators.extend(engine_risks)
        component_scores["engine"] = self._calculate_component_score(engine_risks)
        
        battery_risks = self._analyze_battery(telemetry)
        risk_indicators.extend(battery_risks)
        component_scores["battery"] = self._calculate_component_score(battery_risks)
        
        oil_risks = self._analyze_oil(telemetry)
        risk_indicators.extend(oil_risks)
        component_scores["oil"] = self._calculate_component_score(oil_risks)
        
        brake_risks = self._analyze_brakes(telemetry)
        risk_indicators.extend(brake_risks)
        component_scores["brakes"] = self._calculate_component_score(brake_risks)
        
        tire_risks = self._analyze_tires(telemetry)
        risk_indicators.extend(tire_risks)
        component_scores["tires"] = self._calculate_component_score(tire_risks)
        
        fuel_risks = self._analyze_fuel(telemetry)
        risk_indicators.extend(fuel_risks)
        component_scores["fuel"] = self._calculate_component_score(fuel_risks)
        
        transmission_risks = self._analyze_transmission(telemetry)
        risk_indicators.extend(transmission_risks)
        component_scores["transmission"] = self._calculate_component_score(transmission_risks)
        
        dtc_risks = self._analyze_dtc_codes(telemetry)
        risk_indicators.extend(dtc_risks)
        
        # Calculate overall health score
        health_score = self._calculate_health_score(component_scores)
        
        # Determine overall risk level (Combine ML and Rules)
        rule_risk_level = self._determine_overall_risk(risk_indicators, health_score)
        
        # Prioritize whichever is higher
        final_risk_level = rule_risk_level
        if ml_risk_level == "CRITICAL" and rule_risk_level != "CRITICAL":
            final_risk_level = "CRITICAL"
        elif ml_risk_level == "HIGH" and rule_risk_level == "LOW":
            final_risk_level = "HIGH"
        
        recommended_actions = self._generate_recommendations(risk_indicators)
        
        requires_immediate = final_risk_level == RiskLevel.CRITICAL
        
        return RiskAssessment(
            vehicle_id=vehicle_id,
            timestamp=timestamp,
            overall_risk_level=final_risk_level,
            health_score=health_score,
            risk_indicators=risk_indicators,
            requires_immediate_attention=requires_immediate,
            recommended_actions=recommended_actions,
            confidence_score=ml_confidence,
        )
    
    def _analyze_engine(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        """Analyze engine-related metrics"""
        risks = []
        engine_temp = telemetry.get("engine_temperature_celsius")
        if engine_temp is not None:
            thresholds = self.thresholds["engine_temperature"]
            if engine_temp >= thresholds["critical"]:
                risks.append(RiskIndicator("ENGINE", "engine_temperature", engine_temp, thresholds["warning"], thresholds["critical"], RiskLevel.CRITICAL, f"Engine temperature critically high at {engine_temp}°C"))
            elif engine_temp >= thresholds["warning"]:
                risks.append(RiskIndicator("ENGINE", "engine_temperature", engine_temp, thresholds["warning"], thresholds["critical"], RiskLevel.HIGH, f"Engine temperature elevated at {engine_temp}°C"))
        
        engine_rpm = telemetry.get("engine_rpm")
        if engine_rpm is not None and engine_rpm > 6500:
            risks.append(RiskIndicator("ENGINE", "engine_rpm", engine_rpm, 5500, 6500, RiskLevel.HIGH, f"Engine RPM dangerously high at {engine_rpm}"))
        
        return risks
    
    def _analyze_battery(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        battery_voltage = telemetry.get("battery_voltage")
        if battery_voltage is not None:
            thresholds = self.thresholds["battery_voltage"]
            if battery_voltage <= thresholds["critical"]:
                risks.append(RiskIndicator("BATTERY", "battery_voltage", battery_voltage, thresholds["warning"], thresholds["critical"], RiskLevel.CRITICAL, f"Battery voltage critically low at {battery_voltage}V"))
            elif battery_voltage <= thresholds["warning"]:
                risks.append(RiskIndicator("BATTERY", "battery_voltage", battery_voltage, thresholds["warning"], thresholds["critical"], RiskLevel.MEDIUM, f"Battery voltage low at {battery_voltage}V"))
        return risks
    
    def _analyze_oil(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        oil_level = telemetry.get("oil_level_percent")
        if oil_level is not None:
            thresholds = self.thresholds["oil_level"]
            if oil_level <= thresholds["critical"]:
                risks.append(RiskIndicator("OIL_SYSTEM", "oil_level", oil_level, thresholds["warning"], thresholds["critical"], RiskLevel.CRITICAL, f"Oil level critically low at {oil_level}%"))
            elif oil_level <= thresholds["warning"]:
                risks.append(RiskIndicator("OIL_SYSTEM", "oil_level", oil_level, thresholds["warning"], thresholds["critical"], RiskLevel.MEDIUM, f"Oil level low at {oil_level}%"))
        
        oil_pressure = telemetry.get("oil_pressure")
        if oil_pressure is not None and oil_pressure < 20:
            risks.append(RiskIndicator("OIL_SYSTEM", "oil_pressure", oil_pressure, 25, 20, RiskLevel.HIGH, f"Oil pressure dangerously low at {oil_pressure} PSI"))
        return risks
    
    def _analyze_brakes(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        thresholds = self.thresholds["brake_wear"]
        brake_front = telemetry.get("brake_pad_wear_front_percent")
        if brake_front is not None:
            if brake_front >= thresholds["critical"]:
                risks.append(RiskIndicator("BRAKES", "brake_pad_wear_front", brake_front, thresholds["warning"], thresholds["critical"], RiskLevel.CRITICAL, f"Front brake pads critically worn at {brake_front}%"))
            elif brake_front >= thresholds["warning"]:
                risks.append(RiskIndicator("BRAKES", "brake_pad_wear_front", brake_front, thresholds["warning"], thresholds["critical"], RiskLevel.HIGH, f"Front brake pads worn at {brake_front}%"))
        return risks
    
    def _analyze_tires(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        thresholds = self.thresholds["tire_pressure"]
        for pos in ["fl", "fr", "rl", "rr"]:
            pressure = telemetry.get(f"tire_pressure_{pos}")
            if pressure is not None:
                if pressure <= thresholds["critical"]:
                    risks.append(RiskIndicator("TIRES", f"tire_pressure_{pos}", pressure, thresholds["warning"], thresholds["critical"], RiskLevel.CRITICAL, f"Tire {pos.upper()} pressure critically low at {pressure} PSI"))
                elif pressure <= thresholds["warning"]:
                    risks.append(RiskIndicator("TIRES", f"tire_pressure_{pos}", pressure, thresholds["warning"], thresholds["critical"], RiskLevel.MEDIUM, f"Tire {pos.upper()} pressure low at {pressure} PSI"))
        return risks
    
    def _analyze_fuel(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        fuel_level = telemetry.get("fuel_level_percent")
        if fuel_level is not None:
            if fuel_level <= 5:
                risks.append(RiskIndicator("FUEL_SYSTEM", "fuel_level", fuel_level, 15, 5, RiskLevel.HIGH, f"Fuel level critically low at {fuel_level}%"))
            elif fuel_level <= 15:
                risks.append(RiskIndicator("FUEL_SYSTEM", "fuel_level", fuel_level, 15, 5, RiskLevel.LOW, f"Fuel level low at {fuel_level}%"))
        return risks
    
    def _analyze_transmission(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        trans_temp = telemetry.get("transmission_temperature")
        if trans_temp is not None and trans_temp > 110:
            risks.append(RiskIndicator("TRANSMISSION", "transmission_temperature", trans_temp, 100, 110, RiskLevel.HIGH, f"Transmission temperature high at {trans_temp}°C"))
        return risks
    
    def _analyze_dtc_codes(self, telemetry: Dict[str, Any]) -> List[RiskIndicator]:
        risks = []
        dtc_codes = telemetry.get("dtc_codes")
        if dtc_codes and len(dtc_codes) > 0:
            risks.append(RiskIndicator("DIAGNOSTICS", "dtc_codes", len(dtc_codes), 1, 3, RiskLevel.MEDIUM, f"Active DTCs detected: {', '.join(dtc_codes)}"))
        return risks
    
    def _calculate_component_score(self, risks: List[RiskIndicator]) -> float:
        if not risks: return 100.0
        risk_penalties = {RiskLevel.LOW: 10, RiskLevel.MEDIUM: 25, RiskLevel.HIGH: 45, RiskLevel.CRITICAL: 70}
        total_penalty = sum(risk_penalties.get(r.risk_level, 0) for r in risks)
        return max(0, 100 - total_penalty)
    
    def _calculate_health_score(self, component_scores: Dict[str, float]) -> float:
        weighted_sum = 0.0
        total_weight = 0.0
        for component, score in component_scores.items():
            weight = self.component_weights.get(component, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 100.0
    
    def _determine_overall_risk(self, risks: List[RiskIndicator], health_score: float) -> str:
        if any(r.risk_level == RiskLevel.CRITICAL for r in risks): return RiskLevel.CRITICAL
        if health_score < 40: return RiskLevel.CRITICAL
        elif health_score < 60: return RiskLevel.HIGH
        elif health_score < 80: return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def _generate_recommendations(self, risks: List[RiskIndicator]) -> List[str]:
        recommendations = []
        for risk in risks:
            if risk.risk_level == RiskLevel.CRITICAL: recommendations.append(f"URGENT: {risk.message} - Immediate service required")
            elif risk.risk_level == RiskLevel.HIGH: recommendations.append(f"Schedule service soon: {risk.message}")
            elif risk.risk_level == RiskLevel.MEDIUM: recommendations.append(f"Monitor: {risk.message}")
        return list(set(recommendations))[:10]
    
    def _calculate_confidence(self, telemetry: Dict[str, Any]) -> float:
        return (telemetry.get("quality_score", 100) / 100.0) if telemetry.get("is_valid", True) else 0.5


class TelemetryProcessor:
    """
    Main telemetry processor
    Handles incoming telemetry data and orchestrates processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.risk_analyzer = RiskAnalyzer()
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._is_running: bool = False
        self._alert_callbacks: List = []
        
        logger.info("TelemetryProcessor initialized")
    
    def register_alert_callback(self, callback) -> None:
        """Register callback for alerts"""
        self._alert_callbacks.append(callback)
    
    async def process_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single telemetry reading
        Returns processing result with risk assessment
        """
        start_time = datetime.utcnow()
        vehicle_id = telemetry.get("vehicle_id")
        
        try:
            # Perform risk analysis
            risk_assessment = self.risk_analyzer.analyze(telemetry)
            
            # Store telemetry in database
            await self._store_telemetry(telemetry)
            
            # Check if alerts should be triggered
            if risk_assessment.requires_immediate_attention:
                await self._trigger_alerts(risk_assessment)
            
            # Calculate processing time
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result = {
                "success": True,
                "vehicle_id": vehicle_id,
                "timestamp": telemetry.get("timestamp"),
                "processing_time_ms": processing_time_ms,
                "risk_assessment": {
                    "overall_risk_level": risk_assessment.overall_risk_level,
                    "health_score": risk_assessment.health_score,
                    "requires_immediate_attention": risk_assessment.requires_immediate_attention,
                    "risk_count": len(risk_assessment.risk_indicators),
                    "recommended_actions": risk_assessment.recommended_actions,
                    "confidence_score": risk_assessment.confidence_score,
                },
            }
            
            logger.debug(f"Processed telemetry for {vehicle_id}: health={risk_assessment.health_score}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing telemetry for {vehicle_id}: {e}")
            return {
                "success": False,
                "vehicle_id": vehicle_id,
                "error": str(e),
            }
    
    async def process_batch(self, telemetry_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of telemetry readings"""
        results = []
        
        for telemetry in telemetry_batch:
            result = await self.process_telemetry(telemetry)
            results.append(result)
        
        logger.info(f"Processed batch of {len(telemetry_batch)} telemetry readings")
        return results
    
    async def _store_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Store telemetry data in database"""
        try:
            async with get_async_db_context() as session:
                # 1. Find the vehicle integer ID first
                vehicle_uuid = telemetry.get("vehicle_id")
                vehicle_query = select(Vehicle).where(Vehicle.vehicle_id == vehicle_uuid)
                result = await session.execute(vehicle_query)
                vehicle = result.scalar_one_or_none()

                if not vehicle:
                    logger.warning(f"Telemetry received for unknown vehicle: {vehicle_uuid}")
                    return

                # 2. Create TelemetryData record with the integer ID
                telemetry_record = TelemetryData(
                    vehicle_id=vehicle.id,  # <--- FIXED: using integer ID
                    vehicle_uuid=vehicle_uuid,
                    timestamp=datetime.fromisoformat(telemetry.get("timestamp")),
                    source=telemetry.get("source", "UNKNOWN"),
                    device_id=telemetry.get("device_id"),
                    engine_temperature_celsius=telemetry.get("engine_temperature_celsius"),
                    engine_rpm=telemetry.get("engine_rpm"),
                    engine_load_percent=telemetry.get("engine_load_percent"),
                    battery_voltage=telemetry.get("battery_voltage"),
                    oil_level_percent=telemetry.get("oil_level_percent"),
                    oil_pressure=telemetry.get("oil_pressure"),
                    fuel_level_percent=telemetry.get("fuel_level_percent"),
                    fuel_consumption_rate=telemetry.get("fuel_consumption_rate"),
                    brake_pad_wear_front_percent=telemetry.get("brake_pad_wear_front_percent"),
                    brake_pad_wear_rear_percent=telemetry.get("brake_pad_wear_rear_percent"),
                    tire_pressure_fl=telemetry.get("tire_pressure_fl"),
                    tire_pressure_fr=telemetry.get("tire_pressure_fr"),
                    tire_pressure_rl=telemetry.get("tire_pressure_rl"),
                    tire_pressure_rr=telemetry.get("tire_pressure_rr"),
                    speed_kmh=telemetry.get("speed_kmh"),
                    odometer_km=telemetry.get("odometer_km"),
                    latitude=telemetry.get("latitude"),
                    longitude=telemetry.get("longitude"),
                    dtc_codes=telemetry.get("dtc_codes"),
                    mil_status=telemetry.get("mil_status"),
                    transmission_temperature=telemetry.get("transmission_temperature"),
                    is_valid=telemetry.get("is_valid", True),
                    quality_score=telemetry.get("quality_score"),
                    additional_data=telemetry.get("additional_data"),
                )
                
                session.add(telemetry_record)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing telemetry: {e}")
    
    async def _trigger_alerts(self, risk_assessment: RiskAssessment) -> None:
        """Trigger alerts for critical issues"""
        alert_data = {
            "alert_id": str(uuid.uuid4()),
            "vehicle_id": risk_assessment.vehicle_id,
            "timestamp": risk_assessment.timestamp.isoformat(),
            "risk_level": risk_assessment.overall_risk_level,
            "health_score": risk_assessment.health_score,
            "risks": [
                {
                    "component": r.component,
                    "metric": r.metric_name,
                    "value": r.current_value,
                    "level": r.risk_level,
                    "message": r.message,
                }
                for r in risk_assessment.risk_indicators
                if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            ],
            "recommended_actions": risk_assessment.recommended_actions,
        }
        
        # Notify registered callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Alert triggered for vehicle {risk_assessment.vehicle_id}: {risk_assessment.overall_risk_level}")
    
    async def start_queue_processor(self) -> None:
        """Start background queue processor"""
        self._is_running = True
        logger.info("Starting telemetry queue processor")
        
        while self._is_running:
            try:
                # Get telemetry from queue with timeout
                telemetry = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=5.0
                )
                await self.process_telemetry(telemetry)
                self._processing_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
        
        logger.info("Telemetry queue processor stopped")
    
    def stop_queue_processor(self) -> None:
        """Stop the queue processor"""
        self._is_running = False
    
    async def enqueue_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Add telemetry to processing queue"""
        await self._processing_queue.put(telemetry)
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self._processing_queue.qsize()


# Singleton instances
_processor_instance: Optional[TelemetryProcessor] = None
_analyzer_instance: Optional[RiskAnalyzer] = None


def get_processor() -> TelemetryProcessor:
    """Get or create processor instance"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = TelemetryProcessor()
    return _processor_instance


def get_risk_analyzer() -> RiskAnalyzer:
    """Get or create risk analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = RiskAnalyzer()
    return _analyzer_instance