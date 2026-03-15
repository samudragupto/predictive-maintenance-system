"""
Logging Configuration
Centralized logging setup with structured logging support
"""

import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from contextlib import contextmanager
import uuid
import threading

from backend.config.settings import get_settings

settings = get_settings()

# Thread-local storage for request context
_request_context = threading.local()


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_path: bool = True,
        extra_fields: Dict[str, Any] = None
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_path = include_path
        self.extra_fields = extra_fields or {}
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {}
        
        # Timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Level
        if self.include_level:
            log_data["level"] = record.levelname
        
        # Logger name
        if self.include_logger:
            log_data["logger"] = record.name
        
        # Message
        log_data["message"] = record.getMessage()
        
        # Path info
        if self.include_path:
            log_data["path"] = f"{record.pathname}:{record.lineno}"
            log_data["function"] = record.funcName
        
        # Request context (if available)
        request_id = getattr(_request_context, 'request_id', None)
        if request_id:
            log_data["request_id"] = request_id
        
        correlation_id = getattr(_request_context, 'correlation_id', None)
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                'message', 'asctime'
            ]:
                log_data[key] = value
        
        # Extra fields from formatter
        log_data.update(self.extra_fields)
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored console log formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, fmt: str = None):
        super().__init__(
            fmt or "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # Add request ID if available
        request_id = getattr(_request_context, 'request_id', None)
        if request_id:
            record.msg = f"[{request_id[:8]}] {record.msg}"
        
        return super().format(record)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context to log messages
    """
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Add extra context to kwargs
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs
    
    def with_context(self, **context) -> "LoggerAdapter":
        """Create a new adapter with additional context"""
        new_extra = {**self.extra, **context}
        return LoggerAdapter(self.logger, new_extra)


class RequestLogger:
    """
    Context manager for request-scoped logging
    """
    
    def __init__(
        self,
        request_id: str = None,
        correlation_id: str = None,
        user_id: str = None,
        **extra
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.extra = extra
        self._previous_context = {}
    
    def __enter__(self) -> "RequestLogger":
        # Save previous context
        self._previous_context = {
            'request_id': getattr(_request_context, 'request_id', None),
            'correlation_id': getattr(_request_context, 'correlation_id', None),
            'user_id': getattr(_request_context, 'user_id', None),
        }
        
        # Set new context
        _request_context.request_id = self.request_id
        _request_context.correlation_id = self.correlation_id
        _request_context.user_id = self.user_id
        
        for key, value in self.extra.items():
            setattr(_request_context, key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        for key, value in self._previous_context.items():
            if value is None:
                if hasattr(_request_context, key):
                    delattr(_request_context, key)
            else:
                setattr(_request_context, key, value)
        
        # Clean up extra context
        for key in self.extra.keys():
            if hasattr(_request_context, key):
                delattr(_request_context, key)


def setup_logging(
    level: str = None,
    log_file: str = None,
    json_format: bool = False,
    include_console: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    extra_fields: Dict[str, Any] = None
) -> None:
    """
    Setup application logging
    """
    level = level or settings.LOG_LEVEL
    log_file = log_file or settings.LOG_FILE
    
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        if json_format:
            console_handler.setFormatter(JsonFormatter(extra_fields=extra_fields))
        else:
            console_handler.setFormatter(ColoredFormatter())
        
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        # Always use JSON format for file logs
        file_handler.setFormatter(JsonFormatter(extra_fields=extra_fields))
        
        root_logger.addHandler(file_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized",
        extra={
            "level": level,
            "log_file": log_file,
            "json_format": json_format
        }
    )


def get_logger(name: str, **extra) -> LoggerAdapter:
    """
    Get a logger with optional extra context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, extra)


@contextmanager
def log_context(**context):
    """
    Context manager for adding temporary logging context
    """
    for key, value in context.items():
        setattr(_request_context, key, value)
    
    try:
        yield
    finally:
        for key in context.keys():
            if hasattr(_request_context, key):
                delattr(_request_context, key)


def log_execution_time(logger: logging.Logger = None, level: int = logging.DEBUG):
    """
    Decorator to log function execution time
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        def wrapper(*args, **kwargs):
            start = datetime.now()
            result = func(*args, **kwargs)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            logger.log(
                level,
                f"{func.__name__} executed in {elapsed:.2f}ms",
                extra={"function": func.__name__, "execution_time_ms": elapsed}
            )
            return result
        
        async def async_wrapper(*args, **kwargs):
            start = datetime.now()
            result = await func(*args, **kwargs)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            logger.log(
                level,
                f"{func.__name__} executed in {elapsed:.2f}ms",
                extra={"function": func.__name__, "execution_time_ms": elapsed}
            )
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator