import asyncio
import aiohttp
import random
import time
import sys
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000/api/v1/telemetry/ingest"
TOTAL_VEHICLES = 50  # Must match what you seeded in seed_history.py
CONCURRENT_CARS = 20 # How many cars send data PER SECOND

async def send_telemetry(session, vehicle_index):
    """Send data for a specific vehicle ID"""
    vid = f"VH-{str(vehicle_index).zfill(5)}"
    
    # Generate realistic-looking data
    speed = random.uniform(0, 120)
    rpm = 0 if speed == 0 else random.uniform(800, 4000)
    temp = random.uniform(85, 105)
    
    # Simulate a breakdown for car #10
    if vehicle_index == 10:
        temp = random.uniform(115, 130) # Overheating
    
    payload = {
        "vehicle_id": vid,
        "timestamp": datetime.utcnow().isoformat(),
        "speed_kmh": speed,
        "engine_rpm": rpm,
        "engine_temperature_celsius": temp,
        "battery_voltage": random.uniform(13.2, 14.5),
        "fuel_level_percent": random.uniform(10, 100),
        "oil_level_percent": random.uniform(50, 100),
        "brake_pad_wear_front_percent": random.uniform(10, 40),
        "brake_pad_wear_rear_percent": random.uniform(10, 40),
        "tire_pressure_fl": 32.0, "tire_pressure_fr": 32.0,
        "tire_pressure_rl": 32.0, "tire_pressure_rr": 32.0,
        "source": "SIMULATION"
    }

    try:
        async with session.post(API_URL, json=payload) as response:
            if response.status != 201:
                # 201 Created is success
                # 200 OK is also success (if Kafka queued it)
                if response.status != 200:
                    print(f"⚠️ Error {vid}: {response.status}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

async def run_fleet():
    print(f"🚀 Starting Fleet Simulation ({CONCURRENT_CARS} cars/sec)...")
    print(f"🎯 Target: {API_URL}")
    
    async with aiohttp.ClientSession() as session:
        while True:
            start_time = time.time()
            
            # Pick random cars to be "Active" this second
            # We use range(1, TOTAL+1) because IDs start at VH-00001
            active_indices = random.sample(range(1, TOTAL_VEHICLES + 1), CONCURRENT_CARS)
            
            # Create tasks for all active cars
            tasks = [send_telemetry(session, idx) for idx in active_indices]
            
            # Send all requests in parallel
            await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            print(f"📡 Sent {len(tasks)} readings in {elapsed:.2f}s")
            
            # Wait a bit
            await asyncio.sleep(1)

if __name__ == "__main__":
    # Windows fix for asyncio loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(run_fleet())
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")