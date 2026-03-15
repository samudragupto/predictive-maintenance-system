"""
Main Application
FastAPI application entry point for the Predictive Maintenance System
"""

import asyncio
import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from backend.config.settings import get_settings+
from backend.utils.logger import setup_logging
from backend.utils.exceptions import AppException

settings = get_settings()
logger = logging.getLogger(__name__)

# --- BACKGROUND TASK FOR REAL-TIME DATA ---
async def run_continuous_simulation():
    """Generates telemetry and triggers AI agents in real-time"""
    try:
        # Import agents and services inside the function to avoid circular imports
        from backend.telemetry.simulator import get_simulator
        from backend.services.telemetry_service import get_telemetry_service
        from backend.agents.master_agent import get_master_agent
        import random
        
        logger.info("🚀 Full Real-Time System: STARTED")
        simulator = get_simulator()
        telemetry_service = get_telemetry_service()
        master_agent = get_master_agent()
        
        # Ensure vehicles exist in memory
        if not simulator.vehicles:
            simulator.create_default_fleet(10)

        while True:
            try:
                # 1. Generate & Ingest Telemetry
                batch = await simulator.generate_batch()
                if batch:
                    await telemetry_service.ingest_batch(batch)
                    logger.info(f"⚡ Telemetry: {len(batch)} readings processed")

                    # 2. Randomly trigger AI Workflows (Diagnosis/Scheduling)
                    # We don't want to do this for every car every second (too heavy)
                    # Pick 1 random car from the batch to analyze deeper
                    target_car = random.choice(batch)
                    
                    # If the car has issues (high temp, low oil), trigger the Master Agent
                    needs_analysis = (
                        target_car.get("engine_temperature_celsius", 0) > 100 or 
                        target_car.get("oil_level_percent", 100) < 20 or
                        random.random() < 0.1  # 10% random chance anyway
                    )

                    if needs_analysis:
                        vid = target_car.get("vehicle_id")
                        logger.info(f"🤖 AI Agent: Analyzing vehicle {vid}...")
                        
                        # Trigger Master Agent Workflow
                        # This runs Diagnosis -> Cost -> Scheduling automatically
                        await master_agent.orchestrate_maintenance_workflow(
                            vehicle_id=vid,
                            telemetry_data=target_car
                        )

                # 3. Wait 2 seconds (Fast real-time feel)
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("🛑 Simulation task cancelled")
                break
            except Exception as e:
                logger.error(f"⚠️ Simulation loop error: {e}")
                await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Failed to start simulation task: {e}")

async def run_kafka_consumer():
    """Background task to consume messages from Kafka"""
    from backend.telemetry.kafka_consumer import get_kafka_consumer
    
    logger.info("📡 Kafka Consumer: STARTING...")
    consumer = await get_kafka_consumer()
    
    # This will run forever, processing messages from the queue
    await consumer.start_consuming()
# ============ Lifespan Events ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # STARTUP
    setup_logging(
        level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
        json_format=settings.ENVIRONMENT == "production",
    )
    
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    try:
        from backend.models import init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    # Initialize cache
    try:
        from backend.utils.cache import get_cache
        await get_cache()
        logger.info("Cache initialized successfully")
    except Exception:
        pass

    # Initialize simulator state
    try:
        from backend.telemetry.simulator import get_simulator
        sim = get_simulator()
        sim.create_default_fleet(10)
    except Exception:
        pass

    # --- START BACKGROUND TASKS ---
    
    # 1. Kafka Consumer (if infrastructure is running)
    consumer_task = None
    try:
        from backend.telemetry.kafka_consumer import get_kafka_consumer
        # Just importing and getting instance to prep connection
        # Actual consuming task started below
        consumer_task = asyncio.create_task(run_kafka_consumer())
        logger.info("Background: Kafka Consumer started")
    except Exception as e:
        logger.warning(f"Background: Kafka Consumer skipped ({e})")

    # 2. Simulator (if enabled)
    simulation_task = None
    if settings.SIMULATION_MODE:
        simulation_task = asyncio.create_task(run_continuous_simulation())
        logger.info("Background: Simulation started")

    yield

    # --- SHUTDOWN ---
    logger.info("Shutting down application...")
    
    # Stop Simulator
    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass

    # Stop Kafka Consumer
    if consumer_task:
        consumer_task.cancel()
        try:
            from backend.telemetry.kafka_consumer import get_kafka_consumer
            consumer = await get_kafka_consumer()
            await consumer.stop_consuming()
            await consumer.disconnect()
        except Exception:
            pass

    # Cleanup Producer connections
    try:
        from backend.telemetry.kafka_producer import _producer_instance
        if _producer_instance:
            await _producer_instance.disconnect()
            
        from backend.utils.cache import _cache_manager
        if _cache_manager and hasattr(_cache_manager, '_redis_cache') and _cache_manager._redis_cache:
            await _cache_manager._redis_cache.disconnect()
    except Exception:
        pass

    logger.info("Application shutdown complete!")


# ============ Create FastAPI Application ============

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## AI-Powered Predictive Maintenance System

    A comprehensive multi-agent AI system for vehicle predictive maintenance.
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============ Middleware ============

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests with timing"""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Only log errors or slow requests to keep console clean
        if response.status_code >= 400 or elapsed_ms > 1000:
            logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} ({elapsed_ms}ms)")
            
        return response
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(f"[{request_id}] {request.method} {request.url.path} - ERROR: {e} ({elapsed_ms}ms)")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )


# Exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# ============ Include Routers ============

from backend.routes import api_router
app.include_router(api_router, prefix="/api/v1")


# ============ Root Endpoints ============

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "mode": "real-time simulation" if settings.SIMULATION_MODE else "production",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/health", tags=["Health"])
async def api_health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ============ Run Application ============

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=1,
        reload=settings.DEBUG,
        log_level="info",
    )