"""
Pydantic Schemas
API request/response models for validation and serialization
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


# ============ ENUMS ============

class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HealthStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AppointmentStatusEnum(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ============ BASE SCHEMAS ============

class BaseResponse(BaseModel):
    """Base response schema"""
    success: bool = True
    message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseResponse):
    """Paginated response schema"""
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============ VEHICLE SCHEMAS ============

class VehicleBase(BaseModel):
    """Base vehicle schema"""
    vin: str = Field(..., min_length=17, max_length=17)
    make: str = Field(..., max_length=50)
    model: str = Field(..., max_length=50)
    year: int = Field(..., ge=1900, le=2100)
    license_plate: Optional[str] = Field(None, max_length=20)
    fuel_type: Optional[str] = "PETROL"


class VehicleCreate(VehicleBase):
    """Vehicle creation schema"""
    owner_name: Optional[str] = None
    owner_contact: Optional[str] = None
    fleet_id: Optional[str] = None


class VehicleUpdate(BaseModel):
    """Vehicle update schema"""
    license_plate: Optional[str] = None
    status: Optional[str] = None
    current_mileage_km: Optional[float] = None
    owner_name: Optional[str] = None
    owner_contact: Optional[str] = None


class VehicleResponse(VehicleBase):
    """Vehicle response schema"""
    id: int
    vehicle_id: str
    status: str
    health_status: HealthStatusEnum
    health_score: float
    current_mileage_km: float
    last_service_date: Optional[datetime] = None
    next_service_due_date: Optional[datetime] = None
    is_under_warranty: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VehicleListResponse(PaginatedResponse):
    """Vehicle list response"""
    data: List[VehicleResponse]


# ============ TELEMETRY SCHEMAS ============

class TelemetryBase(BaseModel):
    """Base telemetry schema"""
    vehicle_id: str
    timestamp: datetime


class TelemetryCreate(TelemetryBase):
    """Telemetry creation schema"""
    engine_temperature_celsius: Optional[float] = None
    engine_rpm: Optional[float] = None
    battery_voltage: Optional[float] = None
    oil_level_percent: Optional[float] = None
    fuel_level_percent: Optional[float] = None
    brake_pad_wear_front_percent: Optional[float] = None
    brake_pad_wear_rear_percent: Optional[float] = None
    speed_kmh: Optional[float] = None
    odometer_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tire_pressure_fl: Optional[float] = None
    tire_pressure_fr: Optional[float] = None
    tire_pressure_rl: Optional[float] = None
    tire_pressure_rr: Optional[float] = None
    dtc_codes: Optional[List[str]] = None
    additional_data: Optional[Dict[str, Any]] = None


class TelemetryResponse(TelemetryBase):
    """Telemetry response schema"""
    id: int
    engine_temperature_celsius: Optional[float]
    battery_voltage: Optional[float]
    oil_level_percent: Optional[float]
    fuel_level_percent: Optional[float]
    speed_kmh: Optional[float]
    odometer_km: Optional[float]
    risk_indicators: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class TelemetryBatchCreate(BaseModel):
    """Batch telemetry creation"""
    readings: List[TelemetryCreate]


# ============ DIAGNOSIS SCHEMAS ============

class DiagnosisResponse(BaseModel):
    """Diagnosis response schema"""
    diagnosis_id: str
    vehicle_id: str
    status: str
    overall_risk_level: RiskLevelEnum
    confidence_score: Optional[float]
    health_score: Optional[float]
    summary: Optional[str]
    recommended_actions: Optional[List[str]]
    predicted_failures: Optional[List[Dict[str, Any]]]
    failure_probability: Optional[float]
    estimated_days_to_failure: Optional[int]
    affected_components: Optional[List[str]]
    requires_immediate_attention: bool
    service_recommended: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DiagnosisRequest(BaseModel):
    """Request diagnosis for a vehicle"""
    vehicle_id: str
    include_cost_estimate: bool = True
    auto_schedule: bool = False


class DiagnosisListResponse(PaginatedResponse):
    """Diagnosis list response"""
    data: List[DiagnosisResponse]


# ============ COST ESTIMATE SCHEMAS ============

class CostItemResponse(BaseModel):
    """Cost item response schema"""
    id: int
    category: str
    name: str
    description: Optional[str]
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    part_number: Optional[str]
    is_oem_part: bool
    warranty_covered: bool
    
    model_config = ConfigDict(from_attributes=True)


class CostEstimateResponse(BaseModel):
    """Cost estimate response schema"""
    estimate_id: str
    vehicle_id: str
    status: str
    subtotal_parts: float
    subtotal_labor: float
    subtotal_other: float
    discount_amount: float
    tax_amount: float
    total_estimate: float
    estimate_low: Optional[float]
    estimate_high: Optional[float]
    confidence_score: Optional[float]
    estimated_labor_hours: Optional[float]
    warranty_coverage_amount: float
    summary: Optional[str]
    items: List[CostItemResponse]
    valid_until: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CostEstimateRequest(BaseModel):
    """Request cost estimate"""
    vehicle_id: str
    diagnosis_id: Optional[str] = None
    services_requested: Optional[List[str]] = None


# ============ APPOINTMENT SCHEMAS ============

class AppointmentCreate(BaseModel):
    """Appointment creation schema"""
    vehicle_id: str
    service_center_id: int
    appointment_type: str = "SCHEDULED_MAINTENANCE"
    scheduled_date: datetime
    service_description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


class AppointmentUpdate(BaseModel):
    """Appointment update schema"""
    scheduled_date: Optional[datetime] = None
    status: Optional[str] = None
    service_description: Optional[str] = None
    assigned_technician_id: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    """Appointment response schema"""
    appointment_id: str
    vehicle_id: str
    service_center_id: int
    status: AppointmentStatusEnum
    appointment_type: str
    urgency: str
    scheduled_date: datetime
    estimated_duration_minutes: int
    service_description: Optional[str]
    customer_name: Optional[str]
    assigned_technician_name: Optional[str]
    work_order_number: Optional[str]
    ai_scheduled: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AppointmentListResponse(PaginatedResponse):
    """Appointment list response"""
    data: List[AppointmentResponse]


class AvailableSlotsRequest(BaseModel):
    """Request available time slots"""
    service_center_id: int
    date_from: datetime
    date_to: datetime
    duration_minutes: int = 60


class AvailableSlotResponse(BaseModel):
    """Available slot response"""
    date: datetime
    time_slots: List[str]


# ============ SERVICE CENTER SCHEMAS ============

class ServiceCenterResponse(BaseModel):
    """Service center response schema"""
    center_id: str
    name: str
    center_type: str
    status: str
    address: Dict[str, Any]
    location: Dict[str, float]
    contact: Dict[str, Any]
    operating_hours: Optional[Dict[str, Any]]
    capacity: Dict[str, int]
    services_offered: Optional[List[str]]
    rating: float
    labor_rate: float
    
    model_config = ConfigDict(from_attributes=True)


class ServiceCenterSearchRequest(BaseModel):
    """Search service centers"""
    latitude: float
    longitude: float
    radius_km: float = 50.0
    services_required: Optional[List[str]] = None


# ============ DRIVER BEHAVIOR SCHEMAS ============

class DriverBehaviorResponse(BaseModel):
    """Driver behavior response schema"""
    behavior_id: str
    vehicle_id: str
    driver_id: Optional[str]
    period: Dict[str, Any]
    overall_score: float
    rating: str
    category_scores: Dict[str, Optional[float]]
    statistics: Dict[str, Any]
    events: Dict[str, int]
    risk_score: Optional[float]
    recommendations: Optional[List[str]]
    trend: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class DrivingEventResponse(BaseModel):
    """Driving event response schema"""
    event_id: str
    vehicle_id: str
    event_type: str
    severity: str
    timestamp: datetime
    location: Dict[str, Any]
    speed: Optional[float]
    description: Optional[str]
    acknowledged: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============ FEEDBACK SCHEMAS ============

class FeedbackCreate(BaseModel):
    """Feedback creation schema"""
    vehicle_id: str
    appointment_id: Optional[str] = None
    feedback_type: str = "SERVICE_FEEDBACK"
    overall_rating: Optional[float] = Field(None, ge=1, le=5)
    service_quality_rating: Optional[float] = Field(None, ge=1, le=5)
    timeliness_rating: Optional[float] = Field(None, ge=1, le=5)
    nps_score: Optional[int] = Field(None, ge=0, le=10)
    customer_comments: Optional[str] = None
    issue_resolved: Optional[bool] = None
    prediction_was_accurate: Optional[bool] = None
    actual_issue_description: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback response schema"""
    feedback_id: str
    vehicle_id: str
    feedback_type: str
    ratings: Dict[str, Optional[float]]
    nps_score: Optional[int]
    sentiment: Optional[str]
    customer_comments: Optional[str]
    issue_resolved: Optional[bool]
    prediction_accuracy: Dict[str, Any]
    feedback_date: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============ SECURITY SCHEMAS ============

class SecurityLogResponse(BaseModel):
    """Security log response schema"""
    log_id: str
    timestamp: datetime
    level: str
    actor: Dict[str, Any]
    action: Dict[str, Any]
    resource: Dict[str, Any]
    success: bool
    error: Optional[str]
    ip_address: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class UEBAAlertResponse(BaseModel):
    """UEBA alert response schema"""
    alert_id: str
    detected_at: datetime
    severity: str
    status: str
    alert_type: str
    title: str
    description: str
    entity: Dict[str, Any]
    anomaly_score: float
    risk_score: Optional[float]
    auto_response_taken: bool
    is_false_positive: bool
    
    model_config = ConfigDict(from_attributes=True)


class UEBAAlertUpdate(BaseModel):
    """UEBA alert update schema"""
    status: Optional[str] = None
    investigation_notes: Optional[str] = None
    is_false_positive: Optional[bool] = None
    false_positive_reason: Optional[str] = None


# ============ DASHBOARD SCHEMAS ============

class FleetOverview(BaseModel):
    """Fleet overview for dashboard"""
    total_vehicles: int
    active_vehicles: int
    vehicles_in_service: int
    healthy_vehicles: int
    warning_vehicles: int
    critical_vehicles: int
    average_health_score: float


class AlertSummary(BaseModel):
    """Alert summary for dashboard"""
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    unacknowledged: int


class DashboardResponse(BaseModel):
    """Dashboard response schema"""
    fleet_overview: FleetOverview
    alert_summary: AlertSummary
    recent_diagnoses: List[DiagnosisResponse]
    upcoming_appointments: List[AppointmentResponse]
    recent_alerts: List[UEBAAlertResponse]
    cost_summary: Dict[str, float]


# ============ AGENT SCHEMAS ============

class AgentActionRequest(BaseModel):
    """Request for agent action"""
    action: str
    vehicle_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class AgentActionResponse(BaseModel):
    """Agent action response"""
    success: bool
    action: str
    agent_type: str
    result: Dict[str, Any]
    processing_time_ms: int
    confidence: Optional[float] = None