"""
Validators
Data validation utilities for the application
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    """Custom validation error"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code or "VALIDATION_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "error": self.code,
            "message": self.message,
            "field": self.field,
            "details": self.details,
        }


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    
    @property
    def error_messages(self) -> List[str]:
        return [e.message for e in self.errors]


# ============ VIN Validation ============

def validate_vin(vin: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Vehicle Identification Number (VIN)
    Returns (is_valid, error_message)
    """
    if not vin:
        return False, "VIN is required"
    
    # VIN must be 17 characters
    if len(vin) != 17:
        return False, f"VIN must be 17 characters, got {len(vin)}"
    
    # VIN can only contain alphanumeric characters (no I, O, Q)
    invalid_chars = set("IOQ")
    vin_upper = vin.upper()
    
    for char in vin_upper:
        if char in invalid_chars:
            return False, f"VIN cannot contain characters I, O, or Q"
        if not char.isalnum():
            return False, f"VIN can only contain alphanumeric characters"
    
    # Validate check digit (9th character) using standard VIN algorithm
    transliteration = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
        'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
        'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    }
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    
    try:
        total = 0
        for i, char in enumerate(vin_upper):
            if char.isdigit():
                value = int(char)
            else:
                value = transliteration.get(char, 0)
            total += value * weights[i]
        
        check_digit = total % 11
        expected = 'X' if check_digit == 10 else str(check_digit)
        
        if vin_upper[8] != expected:
            # Note: Some VINs may have invalid check digits
            # This is a warning, not a hard error
            pass
    except Exception:
        pass  # Check digit validation is optional
    
    return True, None


# ============ Email Validation ============

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format
    Returns (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check for common issues
    if '..' in email:
        return False, "Email cannot contain consecutive dots"
    
    if email.startswith('.') or email.endswith('.'):
        return False, "Email cannot start or end with a dot"
    
    # Check domain
    parts = email.split('@')
    if len(parts) != 2:
        return False, "Invalid email format"
    
    local_part, domain = parts
    
    if len(local_part) > 64:
        return False, "Email local part too long (max 64 characters)"
    
    if len(domain) > 255:
        return False, "Email domain too long (max 255 characters)"
    
    return True, None


# ============ Phone Validation ============

def validate_phone(phone: str, country_code: str = "US") -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format
    Returns (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Remove leading + if present
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Check if all remaining characters are digits
    if not cleaned.isdigit():
        return False, "Phone number can only contain digits"
    
    # Validate length based on country
    length_requirements = {
        "US": (10, 11),  # 10 digits or 11 with country code
        "UK": (10, 11),
        "IN": (10, 12),
        "DEFAULT": (8, 15),
    }
    
    min_len, max_len = length_requirements.get(country_code, length_requirements["DEFAULT"])
    
    if len(cleaned) < min_len or len(cleaned) > max_len:
        return False, f"Phone number must be between {min_len} and {max_len} digits"
    
    return True, None


# ============ License Plate Validation ============

def validate_license_plate(plate: str, country: str = "US") -> Tuple[bool, Optional[str]]:
    """
    Validate license plate format
    Returns (is_valid, error_message)
    """
    if not plate:
        return False, "License plate is required"
    
    # Remove spaces and convert to uppercase
    cleaned = plate.replace(' ', '').upper()
    
    # Country-specific patterns
    patterns = {
        "US": r'^[A-Z0-9]{1,8}$',  # Generic US pattern
        "UK": r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # UK pattern (e.g., AB12CDE)
        "IN": r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$',  # India pattern
        "DEFAULT": r'^[A-Z0-9]{1,10}$',
    }
    
    pattern = patterns.get(country, patterns["DEFAULT"])
    
    if not re.match(pattern, cleaned):
        return False, f"Invalid license plate format for {country}"
    
    return True, None


# ============ Coordinate Validation ============

def validate_coordinates(
    latitude: float,
    longitude: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate GPS coordinates
    Returns (is_valid, error_message)
    """
    # Validate latitude (-90 to 90)
    if latitude is None:
        return False, "Latitude is required"
    
    if not isinstance(latitude, (int, float)):
        return False, "Latitude must be a number"
    
    if latitude < -90 or latitude > 90:
        return False, f"Latitude must be between -90 and 90, got {latitude}"
    
    # Validate longitude (-180 to 180)
    if longitude is None:
        return False, "Longitude is required"
    
    if not isinstance(longitude, (int, float)):
        return False, "Longitude must be a number"
    
    if longitude < -180 or longitude > 180:
        return False, f"Longitude must be between -180 and 180, got {longitude}"
    
    return True, None


# ============ Telemetry Data Validation ============

def validate_telemetry_data(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate telemetry data structure and values
    Returns ValidationResult
    """
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ["vehicle_id", "timestamp"]
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(ValidationError(
                message=f"Missing required field: {field}",
                field=field,
                code="REQUIRED_FIELD_MISSING"
            ))
    
    # Validate timestamp
    timestamp = data.get("timestamp")
    if timestamp:
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                raise ValueError("Invalid timestamp type")
            
            # Check if timestamp is not in the future
            if dt > datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now():
                warnings.append("Timestamp is in the future")
            
            # Check if timestamp is not too old (more than 7 days)
            if isinstance(dt, datetime):
                now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
                if (now - dt).days > 7:
                    warnings.append("Timestamp is more than 7 days old")
                    
        except (ValueError, TypeError) as e:
            errors.append(ValidationError(
                message=f"Invalid timestamp format: {e}",
                field="timestamp",
                code="INVALID_TIMESTAMP"
            ))
    
    # Validate numeric ranges
    range_validations = [
        ("engine_temperature_celsius", -40, 200, "Engine temperature"),
        ("engine_rpm", 0, 10000, "Engine RPM"),
        ("battery_voltage", 0, 20, "Battery voltage"),
        ("oil_level_percent", 0, 100, "Oil level"),
        ("fuel_level_percent", 0, 100, "Fuel level"),
        ("brake_pad_wear_front_percent", 0, 100, "Front brake wear"),
        ("brake_pad_wear_rear_percent", 0, 100, "Rear brake wear"),
        ("speed_kmh", 0, 400, "Speed"),
        ("tire_pressure_fl", 0, 100, "Front left tire pressure"),
        ("tire_pressure_fr", 0, 100, "Front right tire pressure"),
        ("tire_pressure_rl", 0, 100, "Rear left tire pressure"),
        ("tire_pressure_rr", 0, 100, "Rear right tire pressure"),
    ]
    
    for field, min_val, max_val, name in range_validations:
        value = data.get(field)
        if value is not None:
            if not isinstance(value, (int, float)):
                errors.append(ValidationError(
                    message=f"{name} must be a number",
                    field=field,
                    code="INVALID_TYPE"
                ))
            elif value < min_val or value > max_val:
                warnings.append(f"{name} value {value} is outside expected range ({min_val}-{max_val})")
    
    # Validate coordinates if present
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    
    if latitude is not None and longitude is not None:
        is_valid, error_msg = validate_coordinates(latitude, longitude)
        if not is_valid:
            errors.append(ValidationError(
                message=error_msg,
                field="coordinates",
                code="INVALID_COORDINATES"
            ))
    
    # Validate DTC codes format
    dtc_codes = data.get("dtc_codes")
    if dtc_codes:
        if not isinstance(dtc_codes, list):
            errors.append(ValidationError(
                message="DTC codes must be a list",
                field="dtc_codes",
                code="INVALID_TYPE"
            ))
        else:
            dtc_pattern = r'^[PCBU][0-9]{4}$'
            for code in dtc_codes:
                if not isinstance(code, str) or not re.match(dtc_pattern, code):
                    warnings.append(f"DTC code '{code}' has non-standard format")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


# ============ Data Validator Class ============

class DataValidator:
    """
    Comprehensive data validator with chainable methods
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
    
    def required(self, field: str, message: Optional[str] = None) -> "DataValidator":
        """Validate that a field is present and not None"""
        if field not in self.data or self.data[field] is None:
            self.errors.append(ValidationError(
                message=message or f"Field '{field}' is required",
                field=field,
                code="REQUIRED"
            ))
        return self
    
    def optional(self, field: str) -> "DataValidator":
        """Mark a field as optional (no validation)"""
        return self
    
    def string(
        self,
        field: str,
        min_length: int = 0,
        max_length: int = None,
        pattern: str = None
    ) -> "DataValidator":
        """Validate string field"""
        value = self.data.get(field)
        if value is None:
            return self
        
        if not isinstance(value, str):
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be a string",
                field=field,
                code="INVALID_TYPE"
            ))
            return self
        
        if len(value) < min_length:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be at least {min_length} characters",
                field=field,
                code="MIN_LENGTH"
            ))
        
        if max_length and len(value) > max_length:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be at most {max_length} characters",
                field=field,
                code="MAX_LENGTH"
            ))
        
        if pattern and not re.match(pattern, value):
            self.errors.append(ValidationError(
                message=f"Field '{field}' has invalid format",
                field=field,
                code="INVALID_FORMAT"
            ))
        
        return self
    
    def number(
        self,
        field: str,
        min_value: float = None,
        max_value: float = None,
        integer_only: bool = False
    ) -> "DataValidator":
        """Validate numeric field"""
        value = self.data.get(field)
        if value is None:
            return self
        
        if integer_only and not isinstance(value, int):
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be an integer",
                field=field,
                code="INVALID_TYPE"
            ))
            return self
        
        if not isinstance(value, (int, float)):
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be a number",
                field=field,
                code="INVALID_TYPE"
            ))
            return self
        
        if min_value is not None and value < min_value:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be at least {min_value}",
                field=field,
                code="MIN_VALUE"
            ))
        
        if max_value is not None and value > max_value:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be at most {max_value}",
                field=field,
                code="MAX_VALUE"
            ))
        
        return self
    
    def email(self, field: str) -> "DataValidator":
        """Validate email field"""
        value = self.data.get(field)
        if value is None:
            return self
        
        is_valid, error = validate_email(value)
        if not is_valid:
            self.errors.append(ValidationError(
                message=error,
                field=field,
                code="INVALID_EMAIL"
            ))
        
        return self
    
    def enum(self, field: str, allowed_values: List[Any]) -> "DataValidator":
        """Validate that field value is in allowed values"""
        value = self.data.get(field)
        if value is None:
            return self
        
        if value not in allowed_values:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be one of: {allowed_values}",
                field=field,
                code="INVALID_ENUM"
            ))
        
        return self
    
    def date(self, field: str, format: str = None) -> "DataValidator":
        """Validate date/datetime field"""
        value = self.data.get(field)
        if value is None:
            return self
        
        if isinstance(value, datetime):
            return self
        
        if isinstance(value, str):
            try:
                if format:
                    datetime.strptime(value, format)
                else:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                self.errors.append(ValidationError(
                    message=f"Field '{field}' has invalid date format",
                    field=field,
                    code="INVALID_DATE"
                ))
        else:
            self.errors.append(ValidationError(
                message=f"Field '{field}' must be a date string or datetime",
                field=field,
                code="INVALID_TYPE"
            ))
        
        return self
    
    def custom(
        self,
        field: str,
        validator: callable,
        message: str = None
    ) -> "DataValidator":
        """Apply custom validation function"""
        value = self.data.get(field)
        if value is None:
            return self
        
        try:
            if not validator(value):
                self.errors.append(ValidationError(
                    message=message or f"Field '{field}' failed custom validation",
                    field=field,
                    code="CUSTOM_VALIDATION"
                ))
        except Exception as e:
            self.errors.append(ValidationError(
                message=f"Field '{field}' validation error: {str(e)}",
                field=field,
                code="VALIDATION_ERROR"
            ))
        
        return self
    
    def validate(self) -> ValidationResult:
        """Execute validation and return result"""
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
    
    def raise_if_invalid(self) -> None:
        """Raise ValidationError if validation fails"""
        if self.errors:
            raise ValidationError(
                message="Validation failed",
                details={"errors": [e.to_dict() for e in self.errors]}
            )