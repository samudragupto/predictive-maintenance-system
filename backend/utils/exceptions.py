"""
Custom Exceptions
Application-specific exception classes
"""

from typing import Dict, Any, Optional, List
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes"""
    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # External Services
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    
    # Database
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    
    # Telemetry
    TELEMETRY_PROCESSING_ERROR = "TELEMETRY_PROCESSING_ERROR"
    TELEMETRY_INVALID_DATA = "TELEMETRY_INVALID_DATA"
    
    # Agent
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_BLOCKED = "AGENT_BLOCKED"
    
    # Vehicle
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    VEHICLE_INVALID_VIN = "VEHICLE_INVALID_VIN"
    
    # Appointment
    APPOINTMENT_NOT_FOUND = "APPOINTMENT_NOT_FOUND"
    APPOINTMENT_CONFLICT = "APPOINTMENT_CONFLICT"
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED"
    
    # Service Center
    SERVICE_CENTER_NOT_FOUND = "SERVICE_CENTER_NOT_FOUND"
    SERVICE_CENTER_UNAVAILABLE = "SERVICE_CENTER_UNAVAILABLE"


class AppException(Exception):
    """
    Base exception class for application-specific exceptions
    All custom exceptions should inherit from this class
    """
    
    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        response = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        
        if self.details:
            response["error"]["details"] = self.details
        
        if self.errors:
            response["error"]["errors"] = self.errors
        
        return response
    
    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', code='{self.code}', status_code={self.status_code})"


class ValidationException(AppException):
    """Exception for validation errors"""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: str = None,
        errors: List[Dict[str, Any]] = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details,
            errors=errors
        )
        self.field = field
        
        if field and not errors:
            self.errors = [{"field": field, "message": message}]


class AuthenticationException(AppException):
    """Exception for authentication failures"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = ErrorCode.AUTHENTICATION_FAILED,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details
        )


class AuthorizationException(AppException):
    """Exception for authorization failures"""
    
    def __init__(
        self,
        message: str = "Access denied",
        required_permission: str = None,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            code=ErrorCode.AUTHORIZATION_FAILED,
            status_code=403,
            details=details
        )


class NotFoundException(AppException):
    """Exception for resource not found"""
    
    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str = None,
        message: str = None,
        details: Dict[str, Any] = None
    ):
        if message is None:
            if resource_id:
                message = f"{resource} with ID '{resource_id}' not found"
            else:
                message = f"{resource} not found"
        
        details = details or {}
        details["resource"] = resource
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


class ConflictException(AppException):
    """Exception for resource conflicts"""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        resource: str = None,
        resource_id: str = None,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if resource:
            details["resource"] = resource
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )


class RateLimitException(AppException):
    """Exception for rate limit exceeded"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        limit: int = None,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        if limit:
            details["limit"] = limit
        
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details
        )
        self.retry_after = retry_after


class ExternalServiceException(AppException):
    """Exception for external service errors"""
    
    def __init__(
        self,
        service_name: str,
        message: str = None,
        code: str = ErrorCode.EXTERNAL_SERVICE_ERROR,
        original_error: Exception = None,
        details: Dict[str, Any] = None
    ):
        if message is None:
            message = f"External service '{service_name}' error"
        
        details = details or {}
        details["service"] = service_name
        if original_error:
            details["original_error"] = str(original_error)
        
        super().__init__(
            message=message,
            code=code,
            status_code=502,
            details=details
        )
        self.service_name = service_name
        self.original_error = original_error


class DatabaseException(AppException):
    """Exception for database errors"""
    
    def __init__(
        self,
        message: str = "Database error",
        operation: str = None,
        original_error: Exception = None,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        if original_error:
            details["original_error"] = str(original_error)
        
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=details
        )
        self.operation = operation
        self.original_error = original_error


class TelemetryException(AppException):
    """Exception for telemetry processing errors"""
    
    def __init__(
        self,
        message: str = "Telemetry processing error",
        vehicle_id: str = None,
        code: str = ErrorCode.TELEMETRY_PROCESSING_ERROR,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if vehicle_id:
            details["vehicle_id"] = vehicle_id
        
        super().__init__(
            message=message,
            code=code,
            status_code=422,
            details=details
        )
        self.vehicle_id = vehicle_id


class AgentException(AppException):
    """Exception for AI agent errors"""
    
    def __init__(
        self,
        message: str = "Agent error",
        agent_type: str = None,
        agent_id: str = None,
        action: str = None,
        code: str = ErrorCode.AGENT_ERROR,
        details: Dict[str, Any] = None
    ):
        details = details or {}
        if agent_type:
            details["agent_type"] = agent_type
        if agent_id:
            details["agent_id"] = agent_id
        if action:
            details["action"] = action
        
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.action = action


# ============ Exception Handler Helper ============

def handle_exception(exception: Exception) -> AppException:
    """
    Convert any exception to AppException
    Useful for consistent error handling
    """
    if isinstance(exception, AppException):
        return exception
    
    # Convert common exceptions
    error_message = str(exception)
    
    # Database errors
    if "database" in error_message.lower() or "sql" in error_message.lower():
        return DatabaseException(
            message="Database operation failed",
            original_error=exception
        )
    
    # Connection errors
    if "connection" in error_message.lower() or "timeout" in error_message.lower():
        return ExternalServiceException(
            service_name="Unknown",
            message="Connection failed",
            original_error=exception
        )
    
    # Default to internal error
    return AppException(
        message="An unexpected error occurred",
        code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
        details={"original_error": str(exception)}
    )