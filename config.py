# -*- coding: utf-8 -*-
"""Configuración central de Kisvic por entorno."""

from __future__ import annotations

import os


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


class BaseConfig:
    SECRET_KEY_DEFAULT = "tu_clave_secreta_aqui"

    SECRET_KEY = os.environ.get("KISVIC_SECRET_KEY", SECRET_KEY_DEFAULT)
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _to_bool(os.environ.get("KISVIC_COOKIE_SECURE", "0"))

    WTF_CSRF_ENABLED = os.environ.get("KISVIC_CSRF_MODE", "phase1").strip().lower() != "off"
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_HEADERS = ["X-CSRFToken"]

    KISVIC_CSRF_MODE = os.environ.get("KISVIC_CSRF_MODE", "phase1").strip().lower()
    KISVIC_CSRF_PROTECTED_ENDPOINTS = os.environ.get("KISVIC_CSRF_PROTECTED_ENDPOINTS", "login")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_active_config():
    env = os.environ.get("KISVIC_ENV", "development").strip().lower()
    if env in {"prod", "production"}:
        return ProductionConfig
    return DevelopmentConfig

