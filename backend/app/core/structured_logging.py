"""Structured JSON logging configuration for production observability.

This module sets up structured JSON logging using python-json-logger,
enabling:
- Machine-readable logs for log aggregation (ELK, Datadog, etc.)
- Request ID propagation for distributed tracing
- Automatic capture of contextual metadata
- Different output formats for dev vs production

Usage:
    from app.core.structured_logging import get_logger

    logger = get_logger(__name__)
    logger.info("user_created", extra={
        "user_id": "123",
        "email": "user@example.com",
    })
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

settings = get_settings()

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
user_email_var: ContextVar[str | None] = ContextVar("user_email", default=None)


class ContextFilter(logging.Filter):
    """Add contextual metadata (request ID, user ID) to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject context variables into log record."""
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get()
        record.user_email = user_email_var.get()
        return True


class ProdJsonFormatter(jsonlogger.JsonFormatter):
    """Production JSON formatter that outputs structured logs."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to JSON log output."""
        super().add_fields(log_record, record, message_dict)

        # Ensure standard fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        # Add context if present
        if hasattr(record, "request_id") and record.request_id != "-":
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id") and record.user_id:
            log_record["user_id"] = record.user_id
        if hasattr(record, "user_email") and record.user_email:
            log_record["user_email"] = record.user_email

        # Add exception info if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        # Add duration if present (for performance tracking)
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms


class DevFormatter(logging.Formatter):
    """Development formatter: human-readable with colors."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)

        # Add context if present
        context = ""
        if hasattr(record, "request_id") and record.request_id != "-":
            context += f" [req:{record.request_id}]"
        if hasattr(record, "user_id") and record.user_id:
            context += f" [user:{record.user_id}]"

        # Format: "timestamp [level] module: message [context]"
        formatted = (
            f"{self.formatTime(record, self.datefmt)} "
            f"{color}[{record.levelname:8s}]{self.RESET} "
            f"{record.name}: "
            f"{record.getMessage()}"
            f"{context}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def configure_logging(environment: str = "development") -> None:
    """Configure logging for development or production.

    Args:
        environment: "development" or "production"
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.addFilter(ContextFilter())

    if environment == "production":
        # Production: structured JSON logs
        formatter = ProdJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            timestamp=True,
        )
    else:
        # Development: human-readable colorized logs
        formatter = DevFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress verbose third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import
configure_logging(settings.ENVIRONMENT)
