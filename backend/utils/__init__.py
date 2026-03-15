"""
Utilities Module
Common utilities, helpers, and shared functionality
"""

from .helpers import (
    generate_uuid,
    generate_id,
    generate_short_id,
    timestamp_now,
    timestamp_to_iso,
    iso_to_timestamp,
    calculate_distance,
    format_currency,
    format_duration,
    chunk_list,
    deep_merge,
    safe_get,
    retry_async,
    Timer,
)

from .validators import (
    validate_vin,
    validate_email,
    validate_phone,
    validate_license_plate,
    validate_coordinates,
    validate_telemetry_data,
    ValidationError,
    DataValidator,
)

from .security import (
    SecurityManager,
    get_security_manager,
    get_current_user, # Added this
    verify_password, # Kept for backward compat if needed
    hash_password,   # Kept for backward compat if needed
    # Removed create_access_token, create_refresh_token
)

from .logger import (
    setup_logging,
    get_logger,
    LoggerAdapter,
    RequestLogger,
)

from .cache import (
    CacheManager,
    get_cache,
    cache_key,
    cached,
)

from .exceptions import (
    AppException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    RateLimitException,
    ExternalServiceException,
    DatabaseException,
    TelemetryException,
    AgentException,
)

__all__ = [
    # Helpers
    "generate_uuid",
    "generate_id",
    "generate_short_id",
    "timestamp_now",
    "timestamp_to_iso",
    "iso_to_timestamp",
    "calculate_distance",
    "format_currency",
    "format_duration",
    "chunk_list",
    "deep_merge",
    "safe_get",
    "retry_async",
    "Timer",
    
    # Validators
    "validate_vin",
    "validate_email",
    "validate_phone",
    "validate_license_plate",
    "validate_coordinates",
    "validate_telemetry_data",
    "ValidationError",
    "DataValidator",
    
    # Security
    "SecurityManager",
    "get_security_manager",
    "get_current_user",
    "verify_password",
    "hash_password",
    
    # Logger
    "setup_logging",
    "get_logger",
    "LoggerAdapter",
    "RequestLogger",
    
    # Cache
    "CacheManager",
    "get_cache",
    "cache_key",
    "cached",
    
    # Exceptions
    "AppException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",
    "ExternalServiceException",
    "DatabaseException",
    "TelemetryException",
    "AgentException",
]