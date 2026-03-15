# backend/seed.py
import asyncio
import logging
import sys
import os

# Ensure backend is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Vehicle, VehicleStatus, get_async_db_context, init_async_db
from backend.models.vehicle import HealthStatus, FuelType
from backend.utils.helpers import timestamp_now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    """Seed the database with 10 initial vehicles"""
    logger.info("Initializing database...")
    await init_async_db()
    
    vehicles_data = [
        {"id": "VH-00001", "make": "Toyota", "model": "Camry", "year": 2022},
        {"id": "VH-00002", "make": "Honda", "model": "Accord", "year": 2021},
        {"id": "VH-00003", "make": "Ford", "model": "F-150", "year": 2023},
        {"id": "VH-00004", "make": "Tesla", "model": "Model 3", "year": 2023, "fuel": "ELECTRIC"},
        {"id": "VH-00005", "make": "Chevrolet", "model": "Silverado", "year": 2022},
        {"id": "VH-00006", "make": "BMW", "model": "3 Series", "year": 2021},
        {"id": "VH-00007", "make": "Mercedes", "model": "C-Class", "year": 2022},
        {"id": "VH-00008", "make": "Audi", "model": "A4", "year": 2021},
        {"id": "VH-00009", "make": "Nissan", "model": "Altima", "year": 2022},
        {"id": "VH-00010", "make": "Hyundai", "model": "Sonata", "year": 2023},
    ]

    async with get_async_db_context() as session:
        for v in vehicles_data:
            # Generate dummy VIN
            vin = f"SIM{v['id'].replace('-', '')}X{v['year']}"
            
            new_vehicle = Vehicle(
                vehicle_id=v["id"],
                vin=vin,
                make=v["make"],
                model=v["model"],
                year=v["year"],
                license_plate=f"ABC-{v['id'].split('-')[1]}",
                fuel_type=FuelType.ELECTRIC if v.get("fuel") == "ELECTRIC" else FuelType.PETROL,
                status=VehicleStatus.ACTIVE,
                health_status=HealthStatus.HEALTHY,
                health_score=100.0,
                current_mileage_km=15000.0,
                is_under_warranty=True,
                created_at=timestamp_now(),
                updated_at=timestamp_now(),
            )
            session.add(new_vehicle)
            logger.info(f"Queued vehicle: {v['id']}")
        
        try:
            await session.commit()
            logger.info("✅ SUCCESS: 10 Vehicles added to SQLite database.")
        except Exception as e:
            logger.warning(f"⚠️  Note: {e}")
            logger.info("Vehicles likely already exist. Continuing...")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())