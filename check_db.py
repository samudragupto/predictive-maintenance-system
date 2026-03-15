import asyncio
import sys
import os
import sqlalchemy
# Fix path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.models import Vehicle, get_async_db_context, init_async_db
from sqlalchemy import select, func

async def check():
    print("--- CHECKING DATABASE ---", flush=True)
    try:
        await init_async_db()
        async with get_async_db_context() as session:
            # Count
            result = await session.execute(select(func.count(Vehicle.id)))
            count = result.scalar()
            print(f"Total Vehicles in DB: {count}", flush=True)
            
            if count > 0:
                # List first 5
                result = await session.execute(select(Vehicle).limit(5))
                cars = result.scalars().all()
                print("First 5 vehicles:", flush=True)
                for c in cars:
                    print(f" - {c.vehicle_id}: {c.make} {c.model}", flush=True)
            else:
                print("⚠️ DATABASE IS EMPTY!", flush=True)
                
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())