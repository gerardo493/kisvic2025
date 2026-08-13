# -*- coding: utf-8 -*-
"""
Blueprint para rutas del Dashboard (vista principal '/' y API '/api/dashboard/...').
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_decorators import login_required
from services.dashboard_service import obtener_estadisticas
from almacenamiento import cargar_datos
from services.filtros_dashboard import obtener_estadisticas_filtradas


ARCHIVO_FACTURAS = "facturas_json/facturas.json"
ARCHIVO_INVENTARIO = "inventario.json"

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    """Ruta principal del Dashboard del sistema."""
    stats = obtener_estadisticas()
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

    total_facturado_usd = sum(float(f.get("total_usd", 0)) for f in facturas.values() if isinstance(f, dict))
    cantidad_facturas = len(facturas)
    promedio_factura_usd = total_facturado_usd / cantidad_facturas if cantidad_facturas > 0 else 0

    advertencia_tasa = None
    if not stats.get("tasa_bcv") or stats.get("tasa_bcv", 0) < 1:
        advertencia_tasa = "¡Advertencia! No se ha podido obtener la tasa BCV actual."

    stats["tasa_bcv_eur"] = 0
    return render_template(
        "index.html",
        **stats,
        advertencia_tasa=advertencia_tasa,
        total_facturado_usd=total_facturado_usd,
        promedio_factura_usd=promedio_factura_usd
    )


@dashboard_bp.route("/api/dashboard-filtros")
@login_required
def api_dashboard_filtros():
    """API para obtener estadísticas filtradas del dashboard."""
    filtro_tipo = request.args.get("tipo")
    filtro_valor = request.args.get("valor")
    try:
        stats = obtener_estadisticas_filtradas(filtro_tipo, filtro_valor)
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@dashboard_bp.route("/api/dashboard/resumen")
def api_dashboard_resumen():
    """API resumen para consumo de frontend desacoplado o dashboard React."""
    autorizado = session.get("usuario") or (
        os.environ.get("KISVIC_PUBLIC_DASHBOARD_API", "0").strip().lower() in ("1", "true", "yes", "on")
    )
    if not autorizado:
        return jsonify({"success": False, "error": "No autorizado"}), 401

    try:
        stats = obtener_estadisticas_filtradas()
        inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
        tasa_bcv = float(stats.get("tasa_bcv", 36.0) or 36.0)

        productos = []
        for pid, p in inventario.items():
            if not isinstance(p, dict):
                continue
            stock = int(float(p.get("cantidad", p.get("stock", 0)) or 0))
            punto_pedido = int(float(p.get("stock_minimo", p.get("punto_pedido", 10)) or 10))
            precio = float(p.get("precio_detal", p.get("precio", 0)) or 0)
            productos.append({
                "id": str(pid),
                "nombre": p.get("nombre", f"Producto {pid}"),
                "sku": p.get("codigo", str(pid)),
                "descripcion": p.get("descripcion", ""),
                "precio": precio,
                "stock": stock,
                "punto_pedido": punto_pedido,
            })

        return jsonify({
            "success": True,
            "data": {
                "metricas": stats,
                "tasa_bcv": tasa_bcv,
                "productos": productos
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
