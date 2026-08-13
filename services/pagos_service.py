# -*- coding: utf-8 -*-
"""
Módulo de servicio para la gestión y procesamiento de pagos/abonos a facturas.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from constants import EstadoFactura, TOLERANCIA_SALDO


def registrar_abono_factura(
    factura: dict,
    monto_pago: float,
    moneda_pago: str = "USD",
    metodo_pago: str = "",
    referencia_pago: str = "",
    banco: str = "",
    captura_path: str | None = None
) -> tuple[dict, dict]:
    """
    Procesa un abono/pago sobre una factura existente, recalculando saldos y estados.
    """
    f = factura.copy()
    if "pagos" not in f or not isinstance(f["pagos"], list):
        f["pagos"] = []

    monto_usd = float(monto_pago)
    tasa_bcv = float(f.get("tasa_bcv", 1.0) or 1.0)

    if moneda_pago == "Bs":
        monto_usd = monto_usd / tasa_bcv if tasa_bcv > 0 else monto_usd

    nuevo_pago = {
        "id": str(uuid.uuid4()),
        "monto": monto_usd,
        "moneda": moneda_pago,
        "metodo": metodo_pago,
        "referencia": referencia_pago,
        "banco": banco,
        "captura_path": captura_path,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    f["pagos"].append(nuevo_pago)

    total_abonado = sum(float(p.get("monto", 0)) for p in f["pagos"] if isinstance(p, dict))
    total_usd = float(f.get("total_usd", 0) or 0)
    saldo_pendiente = max(0.0, total_usd - total_abonado)

    if saldo_pendiente < TOLERANCIA_SALDO or total_abonado >= total_usd:
        saldo_pendiente = 0.0
        estado = EstadoFactura.PAGADA.value
    elif total_abonado > TOLERANCIA_SALDO:
        estado = EstadoFactura.ABONADA.value
    else:
        estado = EstadoFactura.PENDIENTE.value

    f["total_abonado"] = total_abonado
    f["saldo_pendiente"] = saldo_pendiente
    f["estado"] = estado

    return f, nuevo_pago

