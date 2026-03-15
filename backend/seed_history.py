import asyncio
import logging
import random
import sys
import os
from datetime import datetime, timedelta

# Setup path to ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (
    Vehicle, TelemetryData, Diagnosis, ServiceAppointment, 
    ServiceCenter, VehicleStatus, Feedback, RCAReport, CAPAAction,
    init_async_db, get_async_db_context
)
from backend.models.vehicle import HealthStatus, FuelType
from backend.models.diagnosis import RiskLevel, DiagnosisStatus, ComponentCategory
from backend.models.service_appointment import AppointmentStatus, AppointmentType
from backend.models.feedback import FeedbackType, FeedbackSentiment, RCAStatus
from backend.utils.helpers import generate_id, timestamp_now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VEHICLE_COUNT = 50
HISTORY_DAYS = 30
READINGS_PER_DAY = 5

# Correct Make/Model Mapping
FLEET_SPECS = [
    ("Toyota", "Camry", FuelType.PETROL),
    ("Toyota", "Corolla", FuelType.PETROL),
    ("Toyota", "RAV4", FuelType.HYBRID),
    ("Honda", "Accord", FuelType.PETROL),
    ("Honda", "Civic", FuelType.PETROL),
    ("Ford", "F-150", FuelType.PETROL),
    ("Ford", "Mustang", FuelType.PETROL),
    ("Tesla", "Model 3", FuelType.ELECTRIC),
    ("Tesla", "Model Y", FuelType.ELECTRIC),
    ("BMW", "3 Series", FuelType.PETROL),
    ("BMW", "X5", FuelType.PETROL),
]

COMPONENT_OPTIONS = [
    ["ENGINE"],
    ["BRAKES"],
    ["BATTERY"],
    ["TIRES"],
    ["OIL_SYSTEM"],
    ["ENGINE", "BRAKES"],
    ["TIRES", "BRAKES"],
    ["BATTERY", "ELECTRICAL"]
]

async def seed_history():
    await init_async_db()
    logger.info(f"🚀 Generating history for {VEHICLE_COUNT} vehicles...")

    async with get_async_db_context() as session:
        # 0. Create Service Center
        service_center = ServiceCenter(
            center_id="SC-001",
            name="Main Service Center",
            address_line1="123 Mechanic St",
            city="Auto City",
            state="CA",
            country="USA",
            total_bays=10,
            available_bays=10,
            created_at=timestamp_now(),
            updated_at=timestamp_now()
        )
        session.add(service_center)
        await session.flush() # Need ID for appointments
        logger.info("💾 Created Service Center SC-001")

        vehicles = []
        telemetry = []
        diagnoses = []
        appointments = []
        feedbacks = []
        rcas = []

        # 1. Create Vehicles
        for i in range(VEHICLE_COUNT):
            vid = f"VH-{str(i+1).zfill(5)}"
            make, model, f_type = random.choice(FLEET_SPECS)
            year = random.randint(2018, 2024)
            
            # Start with random mileage
            start_mileage = random.uniform(5000, 150000)
            
            v = Vehicle(
                vehicle_id=vid,
                vin=f"VIN{random.randint(1000000000, 9999999999)}",
                make=make,
                model=model,
                year=year,
                fuel_type=f_type,
                status=VehicleStatus.ACTIVE,
                health_status=HealthStatus.HEALTHY,
                health_score=random.uniform(85, 100),
                current_mileage_km=start_mileage,
                is_under_warranty=(year > 2021),
                created_at=timestamp_now() - timedelta(days=HISTORY_DAYS),
                updated_at=timestamp_now()
            )
            
            # 2. Generate Historical Telemetry
            for day in range(HISTORY_DAYS):
                date = timestamp_now() - timedelta(days=HISTORY_DAYS - day)
                for _ in range(READINGS_PER_DAY):
                    t_time = date + timedelta(hours=random.randint(8, 18))
                    t = TelemetryData(
                        vehicle_uuid=vid,
                        timestamp=t_time,
                        speed_kmh=random.uniform(0, 120),
                        engine_temperature_celsius=random.uniform(80, 100),
                        battery_voltage=random.uniform(12.0, 14.5),
                        oil_level_percent=random.uniform(50, 100),
                        fuel_level_percent=random.uniform(10, 100),
                        brake_pad_wear_front_percent=random.uniform(10, 40),
                        brake_pad_wear_rear_percent=random.uniform(10, 40),
                        odometer_km=start_mileage + (day * 50),
                    )
                    telemetry.append(t)

            # 3. Random Diagnosis (30% chance)
            if random.random() < 0.3:
                risk = random.choice([RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL])
                components = random.choice(COMPONENT_OPTIONS)
                
                # Determine scores based on risk
                score = 100.0
                confidence = 0.85
                
                if risk == RiskLevel.CRITICAL:
                    score = random.uniform(20, 45)
                    confidence = 0.95
                elif risk == RiskLevel.HIGH:
                    score = random.uniform(45, 65)
                    confidence = 0.90
                elif risk == RiskLevel.MEDIUM:
                    score = random.uniform(65, 80)
                    confidence = 0.85
                else:
                    score = random.uniform(80, 100)
                    confidence = 0.80
                
                # Update vehicle status
                v.health_status = HealthStatus.CRITICAL if risk == RiskLevel.CRITICAL else \
                                  HealthStatus.WARNING if risk == RiskLevel.HIGH else \
                                  HealthStatus.HEALTHY
                v.health_score = score

                diag_id = f"DG-{generate_id()}"
                d = Diagnosis(
                    diagnosis_id=diag_id,
                    vehicle_uuid=vid,
                    triggered_by="SIMULATION",
                    status=DiagnosisStatus.COMPLETED,
                    overall_risk_level=risk,
                    health_score=score,
                    confidence_score=confidence,
                    affected_components=components,
                    summary=f"Issues detected in: {', '.join(components)}",
                    created_at=timestamp_now() - timedelta(days=random.randint(1, 10))
                )
                diagnoses.append(d)
                
                # Create appointment
                apt_status = AppointmentStatus.COMPLETED if random.random() < 0.5 else AppointmentStatus.SCHEDULED
                
                apt = ServiceAppointment(
                    appointment_id=f"APT-{generate_id()}",
                    vehicle_uuid=vid,
                    service_center_id=service_center.id,
                    status=apt_status,
                    appointment_type=AppointmentType.PREDICTIVE_MAINTENANCE,
                    scheduled_date=timestamp_now() + timedelta(days=random.randint(-5, 7)),
                    created_at=timestamp_now()
                )
                appointments.append(apt)

                # 4. Generate Feedback (only for completed appointments)
                if apt_status == AppointmentStatus.COMPLETED and random.random() < 0.7:
                    rating = random.randint(1, 5)
                    
                    fb = Feedback(
                        feedback_id=f"FB-{generate_id()}",
                        vehicle_uuid=vid,
                        feedback_type=FeedbackType.SERVICE_FEEDBACK,
                        overall_rating=rating,
                        sentiment=FeedbackSentiment.POSITIVE if rating >= 4 else FeedbackSentiment.NEGATIVE if rating <= 2 else FeedbackSentiment.NEUTRAL,
                        customer_comments="Service was efficient" if rating > 3 else "Issue recurred after service",
                        issue_resolved=rating > 2,
                        prediction_was_accurate=True,
                        feedback_date=timestamp_now(),
                        created_at=timestamp_now()
                    )
                    feedbacks.append(fb)
                    
                    # RCA for bad feedback
                    if rating <= 2:
                        rca = RCAReport(
                            rca_id=f"RCA-{generate_id()}",
                            trigger_type="FEEDBACK",
                            status=RCAStatus.OPEN,
                            priority="HIGH",
                            problem_title=f"Low rating for {vid}",
                            problem_description="Customer reported recurring issue after maintenance.",
                            created_at=timestamp_now(),
                            issue_reported_date=timestamp_now()
                        )
                        rcas.append(rca)
            
            vehicles.append(v)

        # Bulk Insert Flow
        logger.info("💾 Writing Vehicles...")
        session.add_all(vehicles)
        await session.flush() # Get IDs

        # Map integer IDs
        v_map = {v.vehicle_id: v.id for v in vehicles}
        
        for t in telemetry:
            t.vehicle_id = v_map[t.vehicle_uuid]
        
        for d in diagnoses:
            d.vehicle_id = v_map[d.vehicle_uuid]
            
        for a in appointments:
            a.vehicle_id = v_map[a.vehicle_uuid]
            
        for f in feedbacks:
            f.vehicle_id = v_map[f.vehicle_uuid]

        # Insert chunks
        logger.info(f"💾 Writing {len(telemetry)} Telemetry records...")
        session.add_all(telemetry)
        
        logger.info(f"💾 Writing {len(diagnoses)} Diagnoses...")
        session.add_all(diagnoses)
        
        logger.info(f"💾 Writing {len(appointments)} Appointments...")
        session.add_all(appointments)
        
        logger.info(f"💾 Writing {len(feedbacks)} Feedback records...")
        session.add_all(feedbacks)
        
        logger.info(f"💾 Writing {len(rcas)} RCA records...")
        session.add_all(rcas)

        await session.commit()
        logger.info("✅ Massive History Seeding Complete!")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_history())