# -*- coding: utf-8 -*-
"""
Módulo de servicio para el procesamiento y creación de facturas con validación SENIAT.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import json
from datetime import datetime
from numeracion_fiscal import control_numeracion
from seguridad_fiscal import seguridad_fiscal

def procesar_nueva_factura(form_data: dict, usuario: str) -> tuple[dict, str]:
    """
    Procesa los datos del formulario de emisión de factura:
    calcula importes, IVA, descuentos y asigna el correlativo fiscal SENIAT.
    """
    numero_fiscal, numero_secuencial = control_numeracion.obtener_siguiente_numero("FACTURA", usuario)

    cliente_id = str(form_data.get("cliente_id", "")).strip()
    fecha = str(form_data.get("fecha", datetime.now().strftime("%Y-%m-%d"))).strip()
    hora_precisa = datetime.now().strftime("%H:%M:%S")

    productos = form_data.getlist("productos[]") if hasattr(form_data, "getlist") else form_data.get("productos[]", [])
    cantidades = form_data.getlist("cantidades[]") if hasattr(form_data, "getlist") else form_data.get("cantidades[]", [])
    precios_raw = form_data.getlist("precios[]") if hasattr(form_data, "getlist") else form_data.get("precios[]", [])
    precios = [float(p) for p in precios_raw if p]

    tasa_bcv = _parse_moneda(form_data.get("tasa_bcv", "36.00")) or 36.00

    subtotal_usd = sum(precios[i] * int(cantidades[i]) for i in range(min(len(precios), len(cantidades))))
    descuento_val = _parse_moneda(form_data.get("descuento", "0"))
    tipo_descuento = form_data.get("tipo_descuento", "bs")

    descuento_total = subtotal_usd * (descuento_val / 100) if tipo_descuento == "porc" else (descuento_val / tasa_bcv)
    iva_porcentaje = _parse_moneda(form_data.get("iva", "0"))
    iva_total = (subtotal_usd - descuento_total) * (iva_porcentaje / 100)

    total_usd = subtotal_usd - descuento_total + iva_total
    total_bs = total_usd * tasa_bcv

    factura_data = {
        "numero": numero_fiscal,
        "numero_secuencial": numero_secuencial,
        "cliente_id": cliente_id,
        "fecha": fecha,
        "hora": hora_precisa,
        "condicion_pago": form_data.get("condicion_pago", "contado"),
        "dias_credito": form_data.get("dias_credito", "30"),
        "productos": productos,
        "cantidades": cantidades,
        "precios": precios,
        "tasa_bcv": tasa_bcv,
        "subtotal_usd": subtotal_usd,
        "descuento_total": descuento_total,
        "iva_porcentaje": iva_porcentaje,
        "iva_total": iva_total,
        "total_usd": total_usd,
        "total_bs": total_bs,
        "total_abonado": 0.0,
        "saldo_pendiente": total_usd,
        "estado": "pendiente",
        "creado_por": usuario,
        "fecha_creacion": datetime.now().isoformat()
    }

    try:
        firma = seguridad_fiscal.generar_hash_documento(
            documento_tipo="FACTURA",
            documento_numero=numero_fiscal,
            monto_total=total_bs,
            fecha=fecha
        )
        factura_data["firma_fiscal"] = firma
    except Exception as e:
        print(f"Advertencia al generar firma fiscal SENIAT: {e}")

    return factura_data, str(numero_secuencial)


def _parse_moneda(val: str | float) -> float:
    """Helper privado para parsear strings monetarias a float de forma segura."""
    if not val:
        return 0.0
    try:
        clean = str(val).replace("$", "").replace("Bs", "").replace(",", ".").strip()
        return float(clean)
    except Exception:
        return 0.0
