"""
Application Settings
Centralized configuration management using Pydantic
"""
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Application
    APP_NAME: str = "Predictive Maintenance System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=4, description="Number of workers")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:admin123@localhost:5432/predictive_maintenance",
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    KAFKA_TELEMETRY_TOPIC: str = Field(
        default="vehicle-telemetry",
        description="Kafka topic for telemetry data"
    )
    KAFKA_ALERTS_TOPIC: str = Field(
        default="maintenance-alerts",
        description="Kafka topic for alerts"
    )
    
    # AI/LLM Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    LLM_MODEL: str = Field(default="gpt-4", description="LLM model to use")
    LLM_TEMPERATURE: float = Field(default=0.1, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=2000, description="Max tokens for LLM response")
    
    # ML Models
    ML_MODELS_PATH: str = Field(
        default="./ml_models",
        description="Path to ML models directory"
    )
    DIAGNOSIS_MODEL_PATH: str = Field(
        default="./ml_models/diagnosis_model.pkl",
        description="Path to diagnosis model"
    )
    FAILURE_PREDICTION_MODEL_PATH: str = Field(
        default="./ml_models/failure_prediction_model.pkl",
        description="Path to failure prediction model"
    )
    
    # Telemetry
    TELEMETRY_INTERVAL_SECONDS: int = Field(
        default=30,
        description="Telemetry collection interval"
    )
    TELEMETRY_BATCH_SIZE: int = Field(
        default=100,
        description="Batch size for telemetry processing"
    )
    SIMULATION_MODE: bool = Field(
        default=True,
        description="Use simulated telemetry data"
    )
    
    # Thresholds for Risk Assessment
    ENGINE_TEMP_WARNING: float = Field(default=100.0, description="Engine temp warning threshold (°C)")
    ENGINE_TEMP_CRITICAL: float = Field(default=110.0, description="Engine temp critical threshold (°C)")
    BRAKE_WEAR_WARNING: float = Field(default=70.0, description="Brake wear warning threshold (%)")
    BRAKE_WEAR_CRITICAL: float = Field(default=85.0, description="Brake wear critical threshold (%)")
    BATTERY_VOLTAGE_LOW: float = Field(default=12.0, description="Battery voltage low threshold (V)")
    BATTERY_VOLTAGE_CRITICAL: float = Field(default=11.5, description="Battery voltage critical threshold (V)")
    OIL_LEVEL_LOW: float = Field(default=30.0, description="Oil level low threshold (%)")
    OIL_LEVEL_CRITICAL: float = Field(default=15.0, description="Oil level critical threshold (%)")
    TIRE_PRESSURE_LOW: float = Field(default=28.0, description="Tire pressure low threshold (PSI)")
    TIRE_PRESSURE_CRITICAL: float = Field(default=25.0, description="Tire pressure critical threshold (PSI)")
    
    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry")
    
    # UEBA Settings
    UEBA_ENABLED: bool = Field(default=True, description="Enable UEBA monitoring")
    UEBA_ANOMALY_THRESHOLD: float = Field(default=0.85, description="Anomaly detection threshold")
    UEBA_BLOCKING_THRESHOLD: float = Field(default=0.95, description="Threshold to block actions")
    UEBA_BASELINE_WINDOW_DAYS: int = Field(default=30, description="Days for baseline behavior")
    
    # Service Centers
    DEFAULT_SERVICE_RADIUS_KM: float = Field(
        default=50.0,
        description="Default radius to search service centers"
    )
    MAX_SCHEDULING_DAYS_AHEAD: int = Field(
        default=30,
        description="Maximum days ahead for scheduling"
    )
    
    # Cost Estimation
    DEFAULT_LABOR_RATE_PER_HOUR: float = Field(
        default=75.0,
        description="Default labor rate per hour ($)"
    )
    COST_ESTIMATION_MARKUP: float = Field(
        default=1.15,
        description="Markup factor for cost estimation"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    LOG_FILE: Optional[str] = Field(default="./logs/app.log", description="Log file path")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Max requests per minute")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, description="Rate limit window")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    # DEBUG PRINT - REMOVE LATER
    print(f"DEBUG: Loaded DATABASE_URL: {s.DATABASE_URL}")
    return s


# Risk Level Enums
class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Component Types
class ComponentType:
    ENGINE = "ENGINE"
    BRAKES = "BRAKES"
    BATTERY = "BATTERY"
    OIL_SYSTEM = "OIL_SYSTEM"
    TRANSMISSION = "TRANSMISSION"
    TIRES = "TIRES"
    COOLING_SYSTEM = "COOLING_SYSTEM"
    ELECTRICAL = "ELECTRICAL"
    SUSPENSION = "SUSPENSION"
    EXHAUST = "EXHAUST"


# Service Status
class ServiceStatus:
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Alert Types
class AlertType:
    MAINTENANCE_REQUIRED = "MAINTENANCE_REQUIRED"
    FAILURE_PREDICTED = "FAILURE_PREDICTED"
    CRITICAL_ISSUE = "CRITICAL_ISSUE"
    SECURITY_ALERT = "SECURITY_ALERT"
    DRIVER_BEHAVIOR = "DRIVER_BEHAVIOR"