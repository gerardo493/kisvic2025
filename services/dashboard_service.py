# -*- coding: utf-8 -*-
"""
Módulo de servicio para la agregación de estadísticas del dashboard.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from datetime import datetime
from almacenamiento import cargar_datos
from services.bcv_service import obtener_tasa_bcv

ARCHIVO_CLIENTES = "clientes.json"
ARCHIVO_INVENTARIO = "inventario.json"
ARCHIVO_FACTURAS = "facturas_json/facturas.json"


def obtener_estadisticas() -> dict:
    """Calcula y compila el resumen de estadísticas para la vista principal del dashboard."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

    mes_actual = datetime.now().month
    tasa_bcv = obtener_tasa_bcv() or 1.0

    facturas_mes = 0
    total_cobrar_usd = 0.0
    total_pagos_recibidos_usd = 0.0
    total_pagos_recibidos_bs = 0.0
    facturas_con_id = []

    for f_id, f in facturas.items():
        if not isinstance(f, dict):
            continue
        factura_copia = f.copy()
        factura_copia["id"] = f_id
        facturas_con_id.append(factura_copia)

        fecha_str = f.get("fecha", "")
        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            if fecha_dt.month == mes_actual:
                facturas_mes += 1
        except Exception:
            pass

        facturado = float(f.get("total_usd", 0))
        abonado = float(f.get("total_abonado", 0))
        saldo = max(0.0, facturado - abonado)
        if saldo > 0:
            total_cobrar_usd += saldo

        for pago in f.get("pagos", []):
            try:
                if fecha_str and datetime.strptime(fecha_str, "%Y-%m-%d").month == mes_actual:
                    monto = float(pago.get("monto", 0))
                    total_pagos_recibidos_usd += monto
                    total_pagos_recibidos_bs += monto * float(f.get("tasa_bcv", tasa_bcv))
            except Exception:
                continue

    ultimas_facturas = sorted(
        facturas_con_id,
        key=lambda x: x.get("fecha", ""),
        reverse=True
    )[:5]

    productos_bajo_stock = [
        p for p in inventario.values()
        if isinstance(p, dict) and int(p.get("cantidad", p.get("stock", 0))) < 10
    ]

    total_cobrar_bs = total_cobrar_usd * tasa_bcv

    return {
        "total_clientes": len(clientes),
        "total_productos": len(inventario),
        "facturas_mes": facturas_mes,
        "total_cobrar": f"{total_cobrar_usd:,.2f}",
        "total_cobrar_usd": total_cobrar_usd,
        "total_cobrar_bs": total_cobrar_bs,
        "tasa_bcv": tasa_bcv,
        "ultimas_facturas": ultimas_facturas,
        "productos_bajo_stock": productos_bajo_stock,
        "total_pagos_recibidos_usd": total_pagos_recibidos_usd,
        "total_pagos_recibidos_bs": total_pagos_recibidos_bs
    }
