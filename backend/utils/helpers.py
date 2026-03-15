"""
Helper Functions
Common utility functions used across the application
"""

import uuid
import hashlib
import asyncio
import functools
import math
import time
from datetime import datetime, timedelta, timezone
from typing import (
    Any, Dict, List, Optional, TypeVar, Callable, 
    Union, Tuple, Awaitable, Iterator
)
from contextlib import contextmanager
import random
import string
import json
import re

T = TypeVar('T')


# ============ ID Generation ============

def generate_uuid() -> str:
    """Generate a UUID4 string"""
    return str(uuid.uuid4())


def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique ID with optional prefix
    Example: VH-A1B2C3D4
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part


def generate_short_id(length: int = 6) -> str:
    """Generate a short alphanumeric ID"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_reference_number(prefix: str, include_date: bool = True) -> str:
    """
    Generate a reference number with date
    Example: APT-20240207-A1B2C3
    """
    random_part = generate_short_id(6).upper()
    
    if include_date:
        date_part = datetime.now().strftime("%Y%m%d")
        return f"{prefix}-{date_part}-{random_part}"
    
    return f"{prefix}-{random_part}"


# ============ Timestamp Utilities ============

def timestamp_now() -> datetime:
    """Get current UTC timestamp (naive)"""
    return datetime.utcnow()


def timestamp_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO format string"""
    if dt is None:
        return None
    return dt.isoformat()


def iso_to_timestamp(iso_string: str) -> Optional[datetime]:
    """Convert ISO string to datetime"""
    if not iso_string:
        return None
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    except ValueError:
        return None


def timestamp_to_epoch(dt: datetime) -> int:
    """Convert datetime to Unix epoch timestamp"""
    return int(dt.timestamp())


def epoch_to_timestamp(epoch: int) -> datetime:
    """Convert Unix epoch to datetime"""
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string
    Example: "5 minutes ago", "2 hours ago"
    """
    if dt is None:
        return "Unknown"
    
    now = timestamp_now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return dt.strftime("%Y-%m-%d")


# ============ Geolocation Utilities ============

def calculate_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    unit: str = "km"
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in km (default) or miles
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance_km = R * c
    
    if unit.lower() == "miles":
        return distance_km * 0.621371
    return distance_km


def get_bounding_box(
    lat: float, lon: float,
    radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Get bounding box coordinates for a radius search
    Returns (min_lat, max_lat, min_lon, max_lon)
    """
    lat_delta = radius_km / 111.0  # 1 degree latitude = ~111 km
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    
    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta,
    )


# ============ Formatting Utilities ============

def format_currency(
    amount: float,
    currency: str = "USD",
    locale: str = "en_US"
) -> str:
    """Format currency value"""
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "INR": "₹",
    }
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string
    Example: 90 -> "1h 30m"
    """
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours}h"
    
    return f"{hours}h {remaining_minutes}m"


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {units[i]}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage"""
    return f"{value:.{decimals}f}%"


# ============ Collection Utilities ============

def chunk_list(lst: List[T], chunk_size: int) -> Iterator[List[T]]:
    """Split a list into chunks of specified size"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def flatten_list(nested_list: List[List[T]]) -> List[T]:
    """Flatten a nested list"""
    return [item for sublist in nested_list for item in sublist]


def unique_list(lst: List[T]) -> List[T]:
    """Remove duplicates while preserving order"""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries
    Override values take precedence
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_get(
    data: Dict,
    path: str,
    default: Any = None,
    separator: str = "."
) -> Any:
    """
    Safely get a nested value from a dictionary
    Example: safe_get(data, "user.profile.name", "Unknown")
    """
    keys = path.split(separator)
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def dict_to_object(data: Dict) -> object:
    """Convert dictionary to object with attribute access"""
    class DictObject:
        def __init__(self, d):
            for key, value in d.items():
                if isinstance(value, dict):
                    setattr(self, key, DictObject(value))
                else:
                    setattr(self, key, value)
    
    return DictObject(data)


# ============ String Utilities ============

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def mask_sensitive(
    text: str,
    visible_start: int = 4,
    visible_end: int = 4,
    mask_char: str = "*"
) -> str:
    """
    Mask sensitive data
    Example: "1234567890" -> "1234****7890"
    """
    if len(text) <= visible_start + visible_end:
        return mask_char * len(text)
    
    start = text[:visible_start]
    end = text[-visible_end:] if visible_end > 0 else ""
    mask_length = len(text) - visible_start - visible_end
    
    return f"{start}{mask_char * mask_length}{end}"


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', camel_str).lower()


# ============ Async Utilities ============

async def retry_async(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> T:
    """
    Retry an async function with exponential backoff
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                if on_retry:
                    on_retry(e, attempt + 1)
                
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                break
    
    raise last_exception


def run_async(coro: Awaitable[T]) -> T:
    """Run async function synchronously"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


async def gather_with_concurrency(
    tasks: List[Awaitable[T]],
    max_concurrent: int = 10
) -> List[T]:
    """Run async tasks with limited concurrency"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[bounded_task(t) for t in tasks])


# ============ Timing Utilities ============

class Timer:
    """Context manager for timing code execution"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed_ms: float = 0
    
    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in milliseconds"""
        if self.end_time:
            return self.elapsed_ms
        return (time.perf_counter() - self.start_time) * 1000
    
    def __str__(self) -> str:
        return f"{self.name}: {self.elapsed:.2f}ms"


@contextmanager
def timed(name: str = "Operation"):
    """Context manager for timing with logging"""
    timer = Timer(name)
    try:
        timer.__enter__()
        yield timer
    finally:
        timer.__exit__(None, None, None)


# ============ Hashing Utilities ============

def hash_string(text: str, algorithm: str = "sha256") -> str:
    """Hash a string using specified algorithm"""
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def hash_dict(data: Dict) -> str:
    """Create a hash of a dictionary for caching/comparison"""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hash_string(json_str)


# ============ Number Utilities ============

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max"""
    return max(min_val, min(max_val, value))


def round_to(value: float, precision: int = 2) -> float:
    """Round to specified decimal places"""
    return round(value, precision)


def percentage_of(part: float, whole: float) -> float:
    """Calculate percentage"""
    if whole == 0:
        return 0.0
    return (part / whole) * 100


def percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change"""
    if old_value == 0:
        return 0.0 if new_value == 0 else 100.0
    return ((new_value - old_value) / abs(old_value)) * 100