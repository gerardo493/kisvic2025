# -*- coding: utf-8 -*-
"""
Blueprint para rutas del mapa avanzado de clientes (/mapa-avanzado).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from flask import Blueprint, render_template, flash, redirect, url_for
from utils.auth_decorators import login_required
from almacenamiento import cargar_datos
from config_maps import get_maps_config

ARCHIVO_CLIENTES = "clientes.json"
ARCHIVO_FACTURAS = "facturas_json/facturas.json"

mapa_bp = Blueprint("mapa", __name__)



@mapa_bp.route("/mapa-avanzado")
@login_required
def mapa_avanzado():
    """Visualización interactiva en mapa de ubicaciones y saldos de clientes."""
    try:
        clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
        facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

        clientes_estadisticas = {}
        total_facturado_mapa = 0.0
        total_por_cobrar_mapa = 0.0
        total_deudores = 0

        for cid, c in clientes.items():
            f_cliente = [f for f in facturas.values() if isinstance(f, dict) and f.get("cliente_id") == cid]
            total_facturado = sum(float(f.get("total_usd", 0) or 0) for f in f_cliente)
            total_abonado = sum(float(f.get("total_abonado", 0) or 0) for f in f_cliente)
            por_cobrar = max(0.0, total_facturado - total_abonado)

            total_facturado_mapa += total_facturado
            total_por_cobrar_mapa += por_cobrar
            if por_cobrar > 0:
                total_deudores += 1

            clientes_estadisticas[cid] = {
                "total_facturas": len(f_cliente),
                "total_facturado": total_facturado,
                "total_abonado": total_abonado,
                "total_por_cobrar": por_cobrar
            }

        maps_config = get_maps_config()

        return render_template(
            "mapa_avanzado.html",
            clientes=clientes,
            clientes_estadisticas=clientes_estadisticas,
            total_facturado_mapa=total_facturado_mapa,
            total_por_cobrar_mapa=total_por_cobrar_mapa,
            total_deudores=total_deudores,
            maps_config=maps_config
        )
    except Exception as e:
        flash(f"Error al cargar el mapa avanzado: {e}", "danger")
        return redirect(url_for("clientes.mostrar_clientes"))
