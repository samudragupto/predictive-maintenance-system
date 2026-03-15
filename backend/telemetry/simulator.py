"""
Telemetry Simulator
Generates realistic vehicle telemetry data for testing and development
Can be replaced with real IoT data sources in production
"""

import random
import math
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class VehicleCondition(str, Enum):
    """Vehicle condition for simulation"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    CRITICAL = "CRITICAL"


class DrivingPattern(str, Enum):
    """Driving pattern simulation"""
    IDLE = "IDLE"
    CITY = "CITY"
    HIGHWAY = "HIGHWAY"
    AGGRESSIVE = "AGGRESSIVE"
    ECO = "ECO"


@dataclass
class VehicleSimulationProfile:
    """
    Profile for simulating a specific vehicle
    Contains baseline values and degradation rates
    """
    vehicle_id: str
    vin: str
    make: str = "Toyota"
    model: str = "Camry"
    year: int = 2022
    mileage: float = 50000.0
    condition: VehicleCondition = VehicleCondition.GOOD
    
    # Engine parameters
    base_engine_temp: float = 90.0
    engine_temp_variance: float = 5.0
    engine_overheating_probability: float = 0.01
    
    # Battery parameters
    base_battery_voltage: float = 12.6
    battery_voltage_variance: float = 0.3
    battery_degradation_rate: float = 0.001
    
    # Oil parameters
    oil_level: float = 85.0
    oil_consumption_rate: float = 0.01
    
    # Brake parameters
    brake_wear_front: float = 30.0
    brake_wear_rear: float = 25.0
    brake_wear_rate: float = 0.005
    
    # Fuel parameters
    fuel_level: float = 75.0
    fuel_consumption_rate: float = 0.1
    
    # Tire parameters
    tire_pressure_base: float = 32.0
    tire_pressure_variance: float = 2.0
    
    # Location (for GPS simulation)
    base_latitude: float = 40.7128
    base_longitude: float = -74.0060
    
    # Current state
    is_running: bool = False
    current_speed: float = 0.0
    current_rpm: float = 0.0
    trip_distance: float = 0.0
    driving_pattern: DrivingPattern = DrivingPattern.IDLE
    
    # Fault injection
    inject_faults: bool = False
    fault_probability: float = 0.05
    active_dtc_codes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Apply condition-based adjustments"""
        condition_factors = {
            VehicleCondition.EXCELLENT: 0.5,
            VehicleCondition.GOOD: 1.0,
            VehicleCondition.FAIR: 1.5,
            VehicleCondition.POOR: 2.5,
            VehicleCondition.CRITICAL: 4.0,
        }
        factor = condition_factors.get(self.condition, 1.0)
        
        self.engine_overheating_probability *= factor
        self.battery_degradation_rate *= factor
        self.oil_consumption_rate *= factor
        self.brake_wear_rate *= factor
        self.fault_probability *= factor


class TelemetrySimulator:
    """
    Main telemetry simulator class
    Generates realistic vehicle telemetry data
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.vehicles: Dict[str, VehicleSimulationProfile] = {}
        self.is_running: bool = False
        self._callbacks: List[Callable] = []
        self._simulation_task: Optional[asyncio.Task] = None
        
        # DTC codes database for fault injection
        self.dtc_codes_database = {
            "engine": ["P0300", "P0301", "P0302", "P0171", "P0174", "P0420", "P0440"],
            "battery": ["P0562", "P0563", "P1549"],
            "transmission": ["P0700", "P0715", "P0720", "P0730"],
            "brakes": ["C0035", "C0040", "C0045", "C0050"],
            "sensors": ["P0100", "P0105", "P0110", "P0115", "P0120"],
            "fuel": ["P0171", "P0172", "P0441", "P0442", "P0455"],
        }
        
        logger.info("TelemetrySimulator initialized")
    
    def register_vehicle(self, profile: VehicleSimulationProfile) -> None:
        """Register a vehicle for simulation"""
        self.vehicles[profile.vehicle_id] = profile
        logger.info(f"Registered vehicle for simulation: {profile.vehicle_id}")
    
    def unregister_vehicle(self, vehicle_id: str) -> None:
        """Unregister a vehicle from simulation"""
        if vehicle_id in self.vehicles:
            del self.vehicles[vehicle_id]
            logger.info(f"Unregistered vehicle from simulation: {vehicle_id}")
    
    def register_callback(self, callback: Callable) -> None:
        """Register a callback for telemetry data"""
        self._callbacks.append(callback)
    
    def create_default_fleet(self, count: int = 10) -> List[VehicleSimulationProfile]:
        """Create a default fleet of vehicles for simulation"""
        makes_models = [
            ("Toyota", "Camry", 2022),
            ("Honda", "Accord", 2021),
            ("Ford", "F-150", 2023),
            ("Chevrolet", "Silverado", 2022),
            ("Tesla", "Model 3", 2023),
            ("BMW", "3 Series", 2021),
            ("Mercedes", "C-Class", 2022),
            ("Audi", "A4", 2021),
            ("Nissan", "Altima", 2022),
            ("Hyundai", "Sonata", 2023),
        ]
        
        conditions = [
            VehicleCondition.EXCELLENT,
            VehicleCondition.GOOD,
            VehicleCondition.GOOD,
            VehicleCondition.GOOD,
            VehicleCondition.FAIR,
            VehicleCondition.FAIR,
            VehicleCondition.POOR,
            VehicleCondition.GOOD,
            VehicleCondition.GOOD,
            VehicleCondition.CRITICAL,
        ]
        
        profiles = []
        for i in range(count):
            make, model, year = makes_models[i % len(makes_models)]
            condition = conditions[i % len(conditions)]
            
            profile = VehicleSimulationProfile(
                vehicle_id=f"VH-{str(i+1).zfill(5)}",
                vin=self._generate_vin(),
                make=make,
                model=model,
                year=year,
                mileage=random.uniform(10000, 150000),
                condition=condition,
                base_latitude=40.7128 + random.uniform(-0.5, 0.5),
                base_longitude=-74.0060 + random.uniform(-0.5, 0.5),
                inject_faults=(condition in [VehicleCondition.POOR, VehicleCondition.CRITICAL]),
            )
            
            # Randomize initial values based on condition
            if condition == VehicleCondition.POOR:
                profile.oil_level = random.uniform(20, 40)
                profile.brake_wear_front = random.uniform(70, 85)
                profile.brake_wear_rear = random.uniform(65, 80)
                profile.base_battery_voltage = random.uniform(11.8, 12.2)
            elif condition == VehicleCondition.CRITICAL:
                profile.oil_level = random.uniform(10, 25)
                profile.brake_wear_front = random.uniform(85, 95)
                profile.brake_wear_rear = random.uniform(80, 92)
                profile.base_battery_voltage = random.uniform(11.2, 11.8)
                profile.active_dtc_codes = random.sample(self.dtc_codes_database["engine"], 2)
            
            profiles.append(profile)
            self.register_vehicle(profile)
        
        logger.info(f"Created default fleet with {count} vehicles")
        return profiles
    
    def _generate_vin(self) -> str:
        """Generate a random VIN"""
        chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
        return ''.join(random.choice(chars) for _ in range(17))
    
    def generate_telemetry(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Generate a single telemetry reading for a vehicle"""
        profile = self.vehicles.get(vehicle_id)
        if not profile:
            logger.warning(f"Vehicle not found: {vehicle_id}")
            return None
        
        # Update driving pattern randomly
        if random.random() < 0.1:  # 10% chance to change pattern
            profile.driving_pattern = random.choice(list(DrivingPattern))
        
        # Generate telemetry based on driving pattern
        telemetry = self._generate_pattern_based_telemetry(profile)
        
        # Update vehicle state
        self._update_vehicle_state(profile, telemetry)
        
        # Inject faults if enabled
        if profile.inject_faults:
            telemetry = self._inject_faults(profile, telemetry)
        
        return telemetry
    
    def _generate_pattern_based_telemetry(self, profile: VehicleSimulationProfile) -> Dict[str, Any]:
        """Generate telemetry based on driving pattern"""
        now = datetime.utcnow()
        
        # Base values based on driving pattern
        pattern_configs = {
            DrivingPattern.IDLE: {
                "speed_range": (0, 0),
                "rpm_range": (700, 900),
                "engine_temp_modifier": -5,
                "fuel_consumption": 0.5,
            },
            DrivingPattern.CITY: {
                "speed_range": (0, 60),
                "rpm_range": (1000, 3000),
                "engine_temp_modifier": 0,
                "fuel_consumption": 8.0,
            },
            DrivingPattern.HIGHWAY: {
                "speed_range": (80, 130),
                "rpm_range": (2000, 3500),
                "engine_temp_modifier": 5,
                "fuel_consumption": 6.0,
            },
            DrivingPattern.AGGRESSIVE: {
                "speed_range": (60, 160),
                "rpm_range": (3000, 6000),
                "engine_temp_modifier": 15,
                "fuel_consumption": 12.0,
            },
            DrivingPattern.ECO: {
                "speed_range": (40, 90),
                "rpm_range": (1200, 2500),
                "engine_temp_modifier": -2,
                "fuel_consumption": 5.0,
            },
        }
        
        config = pattern_configs.get(profile.driving_pattern, pattern_configs[DrivingPattern.IDLE])
        
        # Calculate values
        speed = random.uniform(*config["speed_range"])
        rpm = random.uniform(*config["rpm_range"]) if speed > 0 else random.uniform(700, 900)
        
        # Engine temperature with overheating simulation
        engine_temp = (
            profile.base_engine_temp +
            config["engine_temp_modifier"] +
            random.uniform(-profile.engine_temp_variance, profile.engine_temp_variance)
        )
        
        if random.random() < profile.engine_overheating_probability:
            engine_temp += random.uniform(10, 30)
        
        # Battery voltage with degradation
        battery_voltage = (
            profile.base_battery_voltage +
            random.uniform(-profile.battery_voltage_variance, profile.battery_voltage_variance)
        )
        if speed > 0:  # Charging while running
            battery_voltage += random.uniform(0.5, 1.5)
        
        # Oil level (slowly decreasing)
        oil_level = max(0, profile.oil_level - random.uniform(0, profile.oil_consumption_rate))
        profile.oil_level = oil_level
        
        # Brake wear (slowly increasing)
        if speed > 0:
            profile.brake_wear_front = min(100, profile.brake_wear_front + random.uniform(0, profile.brake_wear_rate))
            profile.brake_wear_rear = min(100, profile.brake_wear_rear + random.uniform(0, profile.brake_wear_rate * 0.8))
        
        # Fuel consumption
        if speed > 0:
            profile.fuel_level = max(0, profile.fuel_level - random.uniform(0, profile.fuel_consumption_rate))
        
        # Tire pressures
        tire_pressures = {
            "fl": profile.tire_pressure_base + random.uniform(-profile.tire_pressure_variance, profile.tire_pressure_variance),
            "fr": profile.tire_pressure_base + random.uniform(-profile.tire_pressure_variance, profile.tire_pressure_variance),
            "rl": profile.tire_pressure_base + random.uniform(-profile.tire_pressure_variance, profile.tire_pressure_variance),
            "rr": profile.tire_pressure_base + random.uniform(-profile.tire_pressure_variance, profile.tire_pressure_variance),
        }
        
        # GPS simulation (random movement)
        if speed > 0:
            distance_km = (speed / 3600) * (self.settings.TELEMETRY_INTERVAL_SECONDS)
            bearing = random.uniform(0, 360)
            lat_change = distance_km * math.cos(math.radians(bearing)) / 111
            lon_change = distance_km * math.sin(math.radians(bearing)) / (111 * math.cos(math.radians(profile.base_latitude)))
            profile.base_latitude += lat_change
            profile.base_longitude += lon_change
            profile.trip_distance += distance_km
        
        # Acceleration (simulated)
        acceleration_x = random.uniform(-2, 3) if profile.driving_pattern == DrivingPattern.AGGRESSIVE else random.uniform(-0.5, 0.5)
        acceleration_y = random.uniform(-1, 1)
        acceleration_z = random.uniform(-0.5, 0.5)
        
        # Build telemetry object
        telemetry = {
            "vehicle_id": profile.vehicle_id,
            "vehicle_uuid": profile.vehicle_id,
            "vin": profile.vin,
            "timestamp": now.isoformat(),
            "received_at": now.isoformat(),
            "source": "SIMULATION",
            
            # Engine
            "engine_temperature_celsius": round(engine_temp, 2),
            "engine_rpm": round(rpm, 0),
            "engine_load_percent": round(random.uniform(10, 80), 2),
            "engine_coolant_temperature": round(engine_temp - random.uniform(5, 15), 2),
            
            # Battery
            "battery_voltage": round(battery_voltage, 2),
            "battery_current": round(random.uniform(-5, 30), 2),
            "alternator_voltage": round(battery_voltage + random.uniform(0.5, 2), 2) if speed > 0 else None,
            
            # Oil
            "oil_level_percent": round(oil_level, 2),
            "oil_pressure": round(random.uniform(25, 65), 2) if speed > 0 else round(random.uniform(10, 25), 2),
            "oil_temperature": round(engine_temp - random.uniform(10, 20), 2),
            
            # Fuel
            "fuel_level_percent": round(profile.fuel_level, 2),
            "fuel_consumption_rate": round(config["fuel_consumption"] + random.uniform(-1, 1), 2),
            
            # Brakes
            "brake_pad_wear_front_percent": round(profile.brake_wear_front, 2),
            "brake_pad_wear_rear_percent": round(profile.brake_wear_rear, 2),
            "brake_fluid_level": round(random.uniform(80, 100), 2),
            "abs_status": True,
            
            # Tires
            "tire_pressure_fl": round(tire_pressures["fl"], 1),
            "tire_pressure_fr": round(tire_pressures["fr"], 1),
            "tire_pressure_rl": round(tire_pressures["rl"], 1),
            "tire_pressure_rr": round(tire_pressures["rr"], 1),
            "tire_temperature_fl": round(random.uniform(25, 45), 1),
            "tire_temperature_fr": round(random.uniform(25, 45), 1),
            "tire_temperature_rl": round(random.uniform(25, 45), 1),
            "tire_temperature_rr": round(random.uniform(25, 45), 1),
            
            # Transmission
            "transmission_temperature": round(random.uniform(70, 95), 2),
            "transmission_fluid_level": round(random.uniform(85, 100), 2),
            "current_gear": self._calculate_gear(speed),
            
            # Speed & Motion
            "speed_kmh": round(speed, 2),
            "acceleration_x": round(acceleration_x, 3),
            "acceleration_y": round(acceleration_y, 3),
            "acceleration_z": round(acceleration_z, 3),
            
            # Odometer
            "odometer_km": round(profile.mileage + profile.trip_distance, 2),
            "trip_distance_km": round(profile.trip_distance, 2),
            
            # Location
            "latitude": round(profile.base_latitude, 6),
            "longitude": round(profile.base_longitude, 6),
            "altitude_m": round(random.uniform(0, 500), 2),
            "heading_degrees": round(random.uniform(0, 360), 2),
            "gps_speed_kmh": round(speed + random.uniform(-2, 2), 2),
            
            # Environment
            "ambient_temperature": round(random.uniform(15, 35), 2),
            "humidity_percent": round(random.uniform(30, 70), 2),
            
            # Diagnostics
            "dtc_codes": profile.active_dtc_codes if profile.active_dtc_codes else None,
            "mil_status": len(profile.active_dtc_codes) > 0,
            
            # Vibration
            "vibration_level": round(random.uniform(0.1, 2.0), 2),
            
            # Metadata
            "driving_pattern": profile.driving_pattern.value,
            "vehicle_condition": profile.condition.value,
            "is_valid": True,
            "quality_score": round(random.uniform(95, 100), 2),
        }
        
        return telemetry
    
    def _calculate_gear(self, speed: float) -> int:
        """Calculate gear based on speed"""
        if speed == 0:
            return 0  # Neutral/Park
        elif speed < 20:
            return 1
        elif speed < 40:
            return 2
        elif speed < 60:
            return 3
        elif speed < 80:
            return 4
        elif speed < 100:
            return 5
        else:
            return 6
    
    def _update_vehicle_state(self, profile: VehicleSimulationProfile, telemetry: Dict[str, Any]) -> None:
        """Update vehicle state after telemetry generation"""
        profile.current_speed = telemetry["speed_kmh"]
        profile.current_rpm = telemetry["engine_rpm"]
        profile.is_running = telemetry["speed_kmh"] > 0 or telemetry["engine_rpm"] > 0
    
    def _inject_faults(self, profile: VehicleSimulationProfile, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Inject faults into telemetry for testing"""
        if random.random() < profile.fault_probability:
            fault_type = random.choice(["engine_overheat", "battery_low", "oil_low", "brake_worn", "dtc"])
            
            if fault_type == "engine_overheat":
                telemetry["engine_temperature_celsius"] = round(random.uniform(110, 130), 2)
                logger.debug(f"Injected engine overheat fault for {profile.vehicle_id}")
                
            elif fault_type == "battery_low":
                telemetry["battery_voltage"] = round(random.uniform(10.5, 11.5), 2)
                logger.debug(f"Injected low battery fault for {profile.vehicle_id}")
                
            elif fault_type == "oil_low":
                telemetry["oil_level_percent"] = round(random.uniform(5, 15), 2)
                profile.oil_level = telemetry["oil_level_percent"]
                logger.debug(f"Injected low oil fault for {profile.vehicle_id}")
                
            elif fault_type == "brake_worn":
                telemetry["brake_pad_wear_front_percent"] = round(random.uniform(90, 98), 2)
                profile.brake_wear_front = telemetry["brake_pad_wear_front_percent"]
                logger.debug(f"Injected brake wear fault for {profile.vehicle_id}")
                
            elif fault_type == "dtc":
                category = random.choice(list(self.dtc_codes_database.keys()))
                new_code = random.choice(self.dtc_codes_database[category])
                if new_code not in profile.active_dtc_codes:
                    profile.active_dtc_codes.append(new_code)
                telemetry["dtc_codes"] = profile.active_dtc_codes
                telemetry["mil_status"] = True
                logger.debug(f"Injected DTC {new_code} for {profile.vehicle_id}")
        
        return telemetry
    
    async def generate_batch(self, vehicle_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate telemetry batch for multiple vehicles"""
        if vehicle_ids is None:
            vehicle_ids = list(self.vehicles.keys())
        
        telemetry_batch = []
        for vehicle_id in vehicle_ids:
            telemetry = self.generate_telemetry(vehicle_id)
            if telemetry:
                telemetry_batch.append(telemetry)
        
        return telemetry_batch
    
    async def start_continuous_simulation(
        self,
        interval_seconds: Optional[int] = None,
        vehicle_ids: Optional[List[str]] = None
    ) -> None:
        """Start continuous telemetry simulation"""
        if self.is_running:
            logger.warning("Simulation is already running")
            return
        
        self.is_running = True
        interval = interval_seconds or self.settings.TELEMETRY_INTERVAL_SECONDS
        
        logger.info(f"Starting continuous simulation with {interval}s interval")
        
        while self.is_running:
            try:
                batch = await self.generate_batch(vehicle_ids)
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(batch)
                        else:
                            callback(batch)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("Simulation cancelled")
                break
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                await asyncio.sleep(1)
        
        self.is_running = False
        logger.info("Continuous simulation stopped")
    
    def stop_simulation(self) -> None:
        """Stop continuous simulation"""
        self.is_running = False
        if self._simulation_task:
            self._simulation_task.cancel()
        logger.info("Simulation stop requested")
    
    def get_vehicle_status(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a simulated vehicle"""
        profile = self.vehicles.get(vehicle_id)
        if not profile:
            return None
        
        return {
            "vehicle_id": profile.vehicle_id,
            "vin": profile.vin,
            "make": profile.make,
            "model": profile.model,
            "year": profile.year,
            "condition": profile.condition.value,
            "mileage": profile.mileage + profile.trip_distance,
            "is_running": profile.is_running,
            "current_speed": profile.current_speed,
            "driving_pattern": profile.driving_pattern.value,
            "oil_level": profile.oil_level,
            "fuel_level": profile.fuel_level,
            "brake_wear_front": profile.brake_wear_front,
            "brake_wear_rear": profile.brake_wear_rear,
            "active_dtc_codes": profile.active_dtc_codes,
            "location": {
                "latitude": profile.base_latitude,
                "longitude": profile.base_longitude,
            },
        }
    
    def get_all_vehicle_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all simulated vehicles"""
        return [
            self.get_vehicle_status(vid)
            for vid in self.vehicles.keys()
        ]


# Singleton instance
_simulator_instance: Optional[TelemetrySimulator] = None


def get_simulator() -> TelemetrySimulator:
    """Get or create simulator instance"""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = TelemetrySimulator()
    return _simulator_instance
