"""
Structured logging setup for the application.

Uses LOG_LEVEL from settings (app.core.config) and configures a JSON formatter
on the root logger. Intended to be called once during application startup.

Usage:
    from app.core.logging import init_logging, get_logger
    init_logging()
    log = get_logger(__name__)
    log.info("service started", extra={"component": "api"})
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings

__all__ = ["init_logging", "get_logger"]


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter with stable keys."""

    default_time_format = "%Y-%m-%dT%H:%M:%S%z"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003 (shadow builtin)
        payload: Dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                self.default_time_format
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include any custom attributes from 'extra' (non-standard LogRecord keys)
        for key, value in record.__dict__.items():
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue
            # Avoid overwriting standard keys
            if key in payload:
                continue
            try:
                json.dumps(value)  # check serializable
                payload[key] = value
            except Exception:
                payload[key] = str(value)

        # Append exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


_configured: bool = False


def _to_log_level(level: str) -> int:
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return mapping.get((level or "INFO").upper(), logging.INFO)


def init_logging() -> None:
    """
    Initialize application logging with a JSON formatter and level from settings.
    Idempotent: safe to call multiple times.
    """
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = _to_log_level(getattr(settings, "log_level", "INFO"))

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicate logs in dev/test
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger with the configured settings."""
    return logging.getLogger(name if name else __name__)
