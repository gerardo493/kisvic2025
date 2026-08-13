# -*- coding: utf-8 -*-
"""
Blueprint para healthcheck (/healthz) y entrega de capturas estáticas.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from datetime import datetime
from flask import Blueprint, jsonify, send_from_directory, abort

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURAS_FOLDER = os.path.join(BASE_PATH, "uploads", "capturas")

health_bp = Blueprint("health", __name__)


@health_bp.route("/uploads/capturas/<filename>")
def serve_captura(filename: str):
    """Sirve archivos de captura desde el directorio persistente."""
    try:
        return send_from_directory(CAPTURAS_FOLDER, filename)
    except Exception as e:
        print(f"Error sirviendo captura {filename}: {e}")
        abort(404)


@health_bp.route("/healthz")
def healthcheck():
    """Verifica el estado de salud de la aplicación y la disponibilidad de directorios críticos."""
    try:
        now = datetime.utcnow().isoformat() + "Z"
        critical_dirs = [
            os.path.join(BASE_PATH, "uploads"),
            CAPTURAS_FOLDER
        ]
        for d in critical_dirs:
            os.makedirs(d, exist_ok=True)

        return jsonify({"status": "ok", "time": now}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500
