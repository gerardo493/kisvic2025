# -*- coding: utf-8 -*-
"""
Módulo de servicio para el registro de bitácora y auditoría fiscal SENIAT.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from datetime import datetime
import requests
from flask import has_request_context, request, session
from seguridad_fiscal import seguridad_fiscal

BITACORA_FILE = "bitacora.log"


def registrar_bitacora(
    usuario: str,
    accion: str,
    detalles: str = "",
    documento_tipo: str = "",
    documento_numero: str = ""
) -> bool:
    """Registra una acción en la bitácora del sistema y en la auditoría fiscal si aplica."""
    ip, ubicacion, lat, lon = _obtener_metadatos_solicitud()

    linea = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"Usuario: {usuario} | Acción: {accion} | Detalles: {detalles} | "
        f"IP: {ip} | Ubicación: {ubicacion} | Coordenadas: {lat},{lon}\n"
    )

    try:
        with open(BITACORA_FILE, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception as e:
        print(f"Error escribiendo en bitácora: {e}")

    _registrar_auditoria_fiscal_si_aplica(
        usuario, accion, detalles, documento_tipo, documento_numero, ip
    )
    return True


def _obtener_metadatos_solicitud() -> tuple[str, str, str, str]:
    """Obtiene IP y datos de geolocalización del contexto de la petición Flask actual."""
    ip, ubicacion, lat, lon = "N/A", "N/A", "", ""

    if not has_request_context():
        return ip, ubicacion, lat, lon

    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
        if ip == "127.0.0.1":
            ip = "190.202.123.123"

        if "ubicacion_precisa" in session:
            ub = session["ubicacion_precisa"]
            return ip, ub.get("texto", ""), ub.get("lat", ""), ub.get("lon", "")

        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                lat = str(data.get("lat", ""))
                lon = str(data.get("lon", ""))
                ciudad = data.get("city", "")
                region = data.get("regionName", "")
                pais = data.get("country", "")
                ubicacion = ", ".join(filter(None, [ciudad, region, pais]))
    except Exception as e:
        print(f"Error resolviendo ubicación en bitácora: {e}")

    return ip, ubicacion, lat, lon


def _registrar_auditoria_fiscal_si_aplica(
    usuario: str,
    accion: str,
    detalles: str,
    documento_tipo: str,
    documento_numero: str,
    ip: str
) -> None:
    """Invoca la auditoría fiscal SENIAT si la acción lo requiere."""
    es_fiscal = bool(
        documento_tipo or documento_numero or
        "factura" in accion.lower() or "fiscal" in accion.lower()
    )
    if es_fiscal:
        try:
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario,
                accion=accion,
                documento_tipo=documento_tipo or "GENERAL",
                documento_numero=documento_numero or "N/A",
                ip_externa=ip,
                detalles=detalles
            )
        except Exception as e:
            error_linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR_LOG_FISCAL: {e}\n"
            try:
                with open(BITACORA_FILE, "a", encoding="utf-8") as f:
                    f.write(error_linea)
            except Exception:
                pass
