"""
Structured logging configuration using structlog + logging stdlib.

Provides both human-readable (development) and JSON (production) output.
Includes request correlation IDs, context variables, and timestamps.

Production logs are formatted as single-line JSON for ELK stack ingestion.
Development logs are formatted as pretty-printed key=value pairs.
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from contextvars import ContextVar
from datetime import UTC
from typing import Any

import structlog

from app.core.config import get_settings

settings = get_settings()

# ─── Context Variables ────────────────────────────────────────────────────
_correlation_id: ContextVar[str] = ContextVar(
    "correlation_id",
    default=""
)
_user_id: ContextVar[str] = ContextVar(
    "user_id",
    default=""
)
_request_id: ContextVar[str] = ContextVar(
    "request_id",
    default=""
)


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context for request tracing."""
    _correlation_id.set(correlation_id)


def get_user_id() -> str:
    """Get current user ID from context."""
    return _user_id.get()


def set_user_id(user_id: str) -> None:
    """Set user ID in context for request tracking."""
    _user_id.set(user_id)


def get_request_id() -> str:
    """Get current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    _request_id.set(request_id)


# ─── Standard Logging Configuration ────────────────────────────────────────
def configure_stdlib_logging() -> None:
    """Configure Python's standard logging module.

    Sets up root logger and structlog integration.
    In development: pretty console output.
    In production: JSON output for ELK/CloudWatch.

    Returns:
        None

    Raises:
        None
    """
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": settings.LOG_LEVEL,
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(log_config)


# ─── Structlog Processors ─────────────────────────────────────────────────
def add_correlation_ids(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add correlation IDs to all log events."""
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    user_id = get_user_id()
    if user_id:
        event_dict["user_id"] = user_id

    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id

    return event_dict


def add_log_level(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def add_timestamp(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ISO 8601 timestamp to event dict."""
    from datetime import datetime

    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def development_renderer(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> str:
    """Pretty-print logs for development (human-readable).

    Args:
        logger: The logger instance.
        method_name: The name of the method called on the logger.
        event_dict: The dictionary of event key-value pairs.

    Returns:
        str: Formatted log message.
    """
    # Extract and format the main event message
    event = event_dict.pop("event", "")

    # Color-code by log level
    level = event_dict.get("level", "INFO").upper()
    color_map = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",   # Green
        "WARNING": "\033[33m", # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    reset = "\033[0m"
    color = color_map.get(level, "")

    # Build the log line
    log_parts = [f"{color}[{level}]{reset}", event]

    # Add context variables if present
    for key in ("correlation_id", "user_id", "request_id"):
        if event_dict.get(key):
            log_parts.append(f"{key}={event_dict.pop(key)}")

    # Add remaining key-value pairs
    for key, value in event_dict.items():
        if key not in ("timestamp",):
            if isinstance(value, str):
                log_parts.append(f"{key}='{value}'")
            else:
                log_parts.append(f"{key}={value}")

    return " ".join(log_parts)


def json_renderer(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> str:
    """Serialize logs to JSON for production (ELK ingestion).

    Args:
        logger: The logger instance.
        method_name: The name of the method called on the logger.
        event_dict: The dictionary of event key-value pairs.

    Returns:
        str: JSON-serialized log line.
    """
    return json.dumps(event_dict, default=str)


# ─── Safe Print Logger for Unicode/Windows Compatibility ──────────────────
class SafePrintLogger:
    """A structlog-compatible logger that safely writes UTF-8 to sys.stdout.

    Prevents UnicodeEncodeError crashes on Windows hosts (like CP1252 streams)
    by writing encoded bytes directly to standard output's binary stream wrapper.
    """

    def __init__(self, file: Any = None) -> None:
        self._file = file or sys.stdout

    def msg(self, message: str) -> None:
        try:
            # Write to the underlying binary buffer if available to avoid encoding issues
            if hasattr(self._file, "buffer") and self._file.buffer is not None:
                self._file.buffer.write((message + "\n").encode("utf-8", errors="replace"))
                self._file.flush()
            else:
                self._file.write(message + "\n")
                self._file.flush()
        except Exception:
            # Fallback to standard write with try-except to avoid crashing the application
            try:
                self._file.write(message.encode("ascii", errors="replace").decode("ascii") + "\n")
                self._file.flush()
            except Exception:
                pass

    # Map all levels to msg
    log = debug = info = warn = warning = error = err = fatal = critical = msg


class SafePrintLoggerFactory:
    """Factory for SafePrintLogger."""

    def __init__(self, file: Any = None) -> None:
        self._file = file

    def __call__(self, *args: Any, **kwargs: Any) -> SafePrintLogger:
        return SafePrintLogger(self._file)


# ─── Setup Function ───────────────────────────────────────────────────────
def setup_logging() -> None:
    """Configure structlog for production or development.

    This function must be called during application initialization.
    It configures both standard logging and structlog with appropriate
    processors and renderers based on the environment.

    Returns:
        None

    Raises:
        None
    """
    # Reconfigure stdout/stderr to UTF-8 to prevent cp1252 encoding crashes on Windows
    import sys
    from contextlib import suppress
    with suppress(AttributeError, OSError):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Configure standard library logging first
    configure_stdlib_logging()

    # Choose renderer based on environment
    if settings.is_production:
        log_renderer = json_renderer
    else:
        log_renderer = development_renderer

    # Configure structlog
    structlog.configure(
        processors=[
            add_log_level,
            add_timestamp,
            add_correlation_ids,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            log_renderer,
        ],
        context_class=dict,
        logger_factory=SafePrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Get the logger and set initial level
    logger = structlog.get_logger()
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    logger.info(
        "logging_configured",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
    )


# ─── Helper Function ──────────────────────────────────────────────────────
def get_logger(name: str) -> Any:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ of the module).

    Returns:
        Logger: A structlog logger instance.
    """
    return structlog.get_logger(name)
