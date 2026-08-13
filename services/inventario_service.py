# -*- coding: utf-8 -*-
"""
Módulo de servicio para el análisis métrico y compilación de datos de inventario.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations


def calcular_metricas_inventario(inventario: dict) -> dict:
    """Calcula las métricas consolidadas del catálogo de inventario."""
    total_productos = len(inventario)
    disponibles = 0
    agotados = 0
    bajo_stock = 0
    valor_total = 0.0
    categorias: dict[str, int] = {}

    for p in inventario.values():
        if not isinstance(p, dict):
            continue
        cant = int(float(p.get("cantidad", 0) or 0))
        precio = float(p.get("precio", 0) or 0)
        stock_min = int(float(p.get("stock_minimo", 5) or 5))
        cat = p.get("categoria", "Sin Categoría")

        valor_total += cant * precio
        categorias[cat] = categorias.get(cat, 0) + 1

        if cant <= 0:
            agotados += 1
        elif cant <= stock_min:
            bajo_stock += 1
            disponibles += 1
        else:
            disponibles += 1

    return {
        "total_productos": total_productos,
        "productos_disponibles": disponibles,
        "productos_agotados": agotados,
        "productos_bajo_stock": bajo_stock,
        "valor_total": valor_total,
        "distribucion_categorias": categorias
    }
