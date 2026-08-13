# -*- coding: utf-8 -*-
"""Observabilidad base: logs estructurados + alertas opcionales."""

from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

import requests

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app_events.log"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if hasattr(record, "event") and isinstance(record.event, dict):
            payload.update(record.event)
        return json.dumps(payload, ensure_ascii=False)


def setup_observability() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("kisvic")
    if logger.handlers:
        return logger

    level_name = os.environ.get("KISVIC_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    logger.info("Observabilidad inicializada", extra={"event": {"event": "observability_init"}})
    return logger


def log_event(logger: logging.Logger, event: str, **data: Any) -> None:
    logger.info(event, extra={"event": {"event": event, **data}})


def log_error(logger: logging.Logger, event: str, error: Exception | str, **data: Any) -> None:
    logger.error(
        event,
        extra={"event": {"event": event, "error": str(error), **data}},
    )


def notify_critical(event: str, message: str, extra: Dict[str, Any] | None = None) -> None:
    webhook = os.environ.get("KISVIC_ALERT_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    payload = {
        "event": event,
        "message": message,
        "extra": extra or {},
    }
    try:
        requests.post(webhook, json=payload, timeout=5)
    except Exception:
        # Nunca romper la app por fallo de alertas.
        pass

