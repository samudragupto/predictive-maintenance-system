"""
Database Models Module
Contains all SQLAlchemy ORM models and database configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator
import logging

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

Base = declarative_base()

# Check if using SQLite
is_sqlite = "sqlite" in settings.DATABASE_URL

# --- SYNC ENGINE ---
sync_url = settings.DATABASE_URL
if not is_sqlite and "postgresql" in sync_url:
    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

sync_connect_args = {"check_same_thread": False} if is_sqlite else {}
sync_engine = create_engine(
    sync_url,
    echo=settings.DEBUG,
    connect_args=sync_connect_args
)

# --- ASYNC ENGINE ---
async_url = settings.DATABASE_URL
if is_sqlite:
    # Ensure it uses aiosqlite driver
    if "sqlite://" in async_url and "aiosqlite" not in async_url:
        async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
else:
    if "postgresql://" in async_url:
        async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

async_connect_args = {"check_same_thread": False} if is_sqlite else {}

async_engine = create_async_engine(
    async_url,
    echo=settings.DEBUG,
    connect_args=async_connect_args
)

# --- SESSIONS ---
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

def get_sync_db() -> Generator[Session, None, None]:
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()

def init_db():
    Base.metadata.create_all(bind=sync_engine)
    logger.info("Database tables created successfully")

async def init_async_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully (async)")

# Import models
from .vehicle import Vehicle, VehicleStatus
from .telemetry import TelemetryData, TelemetrySnapshot
from .diagnosis import Diagnosis, DiagnosisDetail, FailurePrediction
from .cost_estimate import CostEstimate, CostItem
from .service_appointment import ServiceAppointment, AppointmentStatus
from .service_center import ServiceCenter, ServiceCenterCapacity
from .driver_behavior import DriverBehavior, DrivingEvent
from .feedback import Feedback, RCAReport, CAPAAction
from .security_log import SecurityLog, AgentAuditLog, UEBAAlert

__all__ = [
    "Base", "sync_engine", "async_engine",
    "get_sync_db", "get_async_db", "get_db_context", "get_async_db_context",
    "init_db", "init_async_db",
    "Vehicle", "VehicleStatus",
    "TelemetryData", "TelemetrySnapshot",
    "Diagnosis", "DiagnosisDetail", "FailurePrediction",
    "CostEstimate", "CostItem",
    "ServiceAppointment", "AppointmentStatus",
    "ServiceCenter", "ServiceCenterCapacity",
    "DriverBehavior", "DrivingEvent",
    "Feedback", "RCAReport", "CAPAAction",
    "SecurityLog", "AgentAuditLog", "UEBAAlert",
]