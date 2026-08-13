# -*- coding: utf-8 -*-
"""
Blueprint para rutas de API REST auxiliares (/api/productos, /api/clientes, /api/tasa-bcv, etc.).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import requests
from flask import Blueprint, jsonify, request
from almacenamiento import cargar_datos
from services.bcv_service import obtener_tasa_bcv

ARCHIVO_INVENTARIO = "inventario.json"
ARCHIVO_CLIENTES = "clientes.json"

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/productos")
def api_productos():
    """Retorna el catálogo completo de productos en formato JSON."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    return jsonify(inventario)


@api_bp.route("/api/clientes")
def api_clientes():
    """Retorna el directorio completo de clientes en formato JSON."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    return jsonify(clientes)


@api_bp.route("/api/tasa-bcv")
def api_tasa_bcv():
    """Retorna la tasa oficial del BCV vigente."""
    try:
        tasa = obtener_tasa_bcv()
        if tasa:
            return jsonify({"tasa": tasa, "advertencia": False})
        return jsonify({"error": "No se pudo obtener la tasa BCV"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/buscar-clientes")
def api_buscar_clientes():
    """Búsqueda predictiva de clientes por nombre o RIF."""
    q = request.args.get("q", "").strip().lower()
    if not q or len(q) < 2:
        return jsonify({"clientes": []})

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    resultados = []

    for cid, c in clientes.items():
        if not isinstance(c, dict):
            continue
        nombre = c.get("nombre", "").lower()
        rif = c.get("rif", "").lower()
        if q in nombre or q in rif or q in cid.lower():
            resultados.append({
                "id": cid,
                "nombre": c.get("nombre", ""),
                "rif": c.get("rif", ""),
                "email": c.get("email", ""),
                "telefono": c.get("telefono", "")
            })

    return jsonify({"clientes": resultados[:10]})


@api_bp.route("/api/geocodificar")
def api_geocodificar():
    """Geocodifica direcciones mediante OpenStreetMap Nominatim API."""
    direccion = request.args.get("direccion", "").strip()
    if not direccion:
        return jsonify({"error": "Dirección requerida"}), 400

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": direccion, "format": "json", "limit": 1}
        headers = {"User-Agent": "KISVIC2025/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"Error de geocodificación: {e}"}), 500
