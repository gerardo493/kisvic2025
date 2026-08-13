# -*- coding: utf-8 -*-
"""
Blueprint para rutas de cuentas por cobrar (/cuentas-por-cobrar).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from utils.auth_decorators import login_required
from almacenamiento import cargar_datos
from services.bcv_service import obtener_tasa_bcv
from constants import (
    EstadoFactura,
    TOLERANCIA_SALDO,
    DIAS_VENCIMIENTO_DEFAULT,
    TASA_BCV_FALLBACK,
)

logger = logging.getLogger(__name__)

ARCHIVO_FACTURAS = "facturas_json/facturas.json"
ARCHIVO_CLIENTES = "clientes.json"

cuentas_bp = Blueprint("cuentas", __name__)


@cuentas_bp.route("/cuentas-por-cobrar")
@login_required
def mostrar_cuentas_por_cobrar():
    """Visualiza el estado de las cuentas por cobrar, abonadas y cobradas."""
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}

    filtro_raw = request.args.get("estado", "por_cobrar")
    filtro_estado = EstadoFactura.from_string(filtro_raw)
    filtro = request.args.get("estado", "por_cobrar").lower()

    cliente_param = request.args.get("cliente", "").strip()
    mes_param = request.args.get("mes", "").strip()
    anio_param = request.args.get("anio", "").strip()
    solo_vencidas = request.args.get("solo_vencidas", "").strip() == "1"

    dias_vencimiento_param = request.args.get("dias_vencimiento", "").strip()
    try:
        dias_vencimiento_limite = int(dias_vencimiento_param) if dias_vencimiento_param else DIAS_VENCIMIENTO_DEFAULT
    except ValueError:
        dias_vencimiento_limite = DIAS_VENCIMIENTO_DEFAULT

    tasa_obtenida = obtener_tasa_bcv()
    if tasa_obtenida and tasa_obtenida > 0:
        tasa_bcv = float(tasa_obtenida)
        tasa_bcv_desactualizada = False
    else:
        tasa_bcv = TASA_BCV_FALLBACK
        tasa_bcv_desactualizada = True

    hoy = datetime.now()

    cuentas_filtradas = {}
    total_por_cobrar_usd = 0.0
    total_abonadas_usd = 0.0
    total_cobradas_usd = 0.0
    vencidas_count = 0

    list_por_cobrar = []
    list_abonadas = []
    list_cobradas = []

    anios_set = set()

    for f_id, f in facturas.items():
        if not isinstance(f, dict):
            continue

        c_id = str(f.get("cliente_id", ""))
        if cliente_param and c_id != cliente_param:
            continue

        fecha_str = f.get("fecha", "")
        f_date = None
        if fecha_str:
            try:
                f_date = datetime.strptime(str(fecha_str).strip(), "%Y-%m-%d")
                anios_set.add(f_date.year)
                if mes_param and f_date.month != int(mes_param):
                    continue
                if anio_param and f_date.year != int(anio_param):
                    continue
            except Exception as e:
                logger.warning(
                    f"Error parseando fecha '{fecha_str}' en factura ID '{f_id}': {e}"
                )
                if mes_param or anio_param:
                    continue

        total_usd = float(f.get("total_usd", 0) or 0)
        total_abonado = float(f.get("total_abonado", 0) or 0)
        saldo_pendiente = max(0.0, total_usd - total_abonado)

        if saldo_pendiente < TOLERANCIA_SALDO or (total_usd > 0 and total_abonado >= total_usd):
            estado_enum = EstadoFactura.PAGADA
            list_cobradas.append(f_id)
            total_cobradas_usd += total_usd
        elif total_abonado > TOLERANCIA_SALDO:
            estado_enum = EstadoFactura.ABONADA
            list_abonadas.append(f_id)
            total_abonadas_usd += total_abonado
            total_por_cobrar_usd += saldo_pendiente
        else:
            estado_enum = EstadoFactura.PENDIENTE
            list_por_cobrar.append(f_id)
            total_por_cobrar_usd += saldo_pendiente

        vencida = False
        if saldo_pendiente >= TOLERANCIA_SALDO and f_date is not None:
            if (hoy - f_date).days > dias_vencimiento_limite:
                vencida = True
                vencidas_count += 1

        if solo_vencidas and not vencida:
            continue

        if filtro == "todas" or estado_enum.key_filtro == filtro or estado_enum.value == filtro:
            cliente_obj = clientes.get(c_id, {})
            nombre_cliente = (
                cliente_obj.get("nombre", f.get("cliente_nombre", f"Cliente {c_id}"))
                if isinstance(cliente_obj, dict)
                else f"Cliente {c_id}"
            )
            rif_cliente = (
                cliente_obj.get("rif", f.get("cliente_rif", ""))
                if isinstance(cliente_obj, dict)
                else ""
            )

            pagos = f.get("pagos", [])
            ultimo_pago = pagos[-1] if isinstance(pagos, list) and pagos else {}

            raw_id = f.get("id")
            num_factura = f.get("numero_factura")
            factura_key_safe = (
                str(raw_id) if raw_id is not None and str(raw_id).strip() != "" else str(num_factura or f_id)
            )

            raw_num_str = str(num_factura or f_id)
            if len(raw_num_str) > 16 and "-" in raw_num_str:
                clean_hex = raw_num_str.replace("-", "")
                numero_display = f"FAC-{clean_hex[:8].upper()}"
            else:
                numero_display = raw_num_str

            cuentas_filtradas[factura_key_safe] = {
                "numero_factura": num_factura or f_id,
                "numero_factura_display": numero_display,
                "factura_id": factura_key_safe,
                "nota_entrega_origen": f.get("nota_entrega_origen", ""),
                "cliente_id": c_id,
                "cliente_nombre": nombre_cliente,
                "rif": rif_cliente,
                "fecha_emision": fecha_str if f_date else (fecha_str or "Fecha inválida"),
                "total_usd": total_usd,
                "abonado_usd": total_abonado,
                "saldo_pendiente": saldo_pendiente,
                "vencida": vencida,
                "estado": estado_enum.label,
                "estado_key": estado_enum.key_filtro,
                "estado_badge": estado_enum.badge_class,
                "fecha_ultimo_abono": ultimo_pago.get("fecha", ""),
                "tipo_pago": ultimo_pago.get("metodo", ultimo_pago.get("tipo", "")),
            }


    clientes_disponibles = sorted(
        [
            {"id": cid, "nombre": cdata.get("nombre", cid)}
            for cid, cdata in clientes.items()
            if isinstance(cdata, dict)
        ],
        key=lambda x: str(x["nombre"]).lower(),
    )

    anios_disponibles = sorted(list(anios_set), reverse=True) or [hoy.year]

    return render_template(
        "cuentas_por_cobrar.html",
        cuentas_filtradas=cuentas_filtradas,
        clientes_disponibles=clientes_disponibles,
        anios_disponibles=anios_disponibles,
        filtro_estado=filtro,
        total_por_cobrar=list_por_cobrar,
        total_abonadas=list_abonadas,
        total_cobradas=list_cobradas,
        total_por_cobrar_usd=total_por_cobrar_usd,
        total_abonadas_usd=total_abonadas_usd,
        total_cobradas_usd=total_cobradas_usd,
        vencidas_count=vencidas_count,
        total_por_cobrar_bs=total_por_cobrar_usd * tasa_bcv,
        tasa_bcv=tasa_bcv,
        tasa_bcv_desactualizada=tasa_bcv_desactualizada,
        dias_vencimiento_limite=dias_vencimiento_limite,
    )


@cuentas_bp.route("/cuentas-por-cobrar/metricas")
@login_required
def mostrar_dashboard_metricas():
    """Visualización de métricas avanzadas y analítica neumórfica."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

    anios_set = set()
    for f in facturas.values():
        if isinstance(f, dict) and f.get("fecha"):
            try:
                dt = datetime.strptime(str(f["fecha"]).strip(), "%Y-%m-%d")
                anios_set.add(dt.year)
            except Exception:
                pass

    hoy = datetime.now()
    clientes_disponibles = sorted(
        [
            {"id": cid, "nombre": cdata.get("nombre", cid)}
            for cid, cdata in clientes.items()
            if isinstance(cdata, dict)
        ],
        key=lambda x: str(x["nombre"]).lower(),
    )
    anios_disponibles = sorted(list(anios_set), reverse=True) or [hoy.year]

    return render_template(
        "dashboard_metricas.html",
        clientes_disponibles=clientes_disponibles,
        anios_disponibles=anios_disponibles,
    )


@cuentas_bp.route("/cuentas-por-cobrar/api/metricas")
@login_required
def api_metricas_cuentas():
    """API JSON para analítica de cuentas por cobrar."""
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}

    cliente_param = request.args.get("cliente", "").strip()
    mes_param = request.args.get("mes", "").strip()
    anio_param = request.args.get("anio", "").strip()

    hoy = datetime.now()

    total_facturado = 0.0
    total_cobrado = 0.0
    total_por_cobrar = 0.0
    total_abonadas_monto = 0.0
    total_cobradas_monto = 0.0

    distribucion = {
        "por_cobrar": 0.0,
        "abonada": 0.0,
        "cobrada": 0.0,
    }

    aging = {
        "rango_0_30": 0.0,
        "rango_31_60": 0.0,
        "rango_61_90": 0.0,
        "rango_mas_90": 0.0,
    }

    deuda_por_cliente = {}
    dias_cobro_lista = []

    vencidas_count = 0
    vencidas_monto = 0.0

    # Diccionario para evolución mensual de los últimos 12 meses
    meses_map = {}
    for i in range(11, -1, -1):
        year = hoy.year
        month = hoy.month - i
        while month <= 0:
            month += 12
            year -= 1
        key = f"{year:04d}-{month:02d}"
        meses_map[key] = {"facturado": 0.0, "cobrado": 0.0}

    for f_id, f in facturas.items():
        if not isinstance(f, dict):
            continue

        c_id = str(f.get("cliente_id", ""))
        if cliente_param and c_id != cliente_param:
            continue

        fecha_str = f.get("fecha", "")
        f_date = None
        if fecha_str:
            try:
                f_date = datetime.strptime(str(fecha_str).strip()[:10], "%Y-%m-%d")
                if mes_param and f_date.month != int(mes_param):
                    continue
                if anio_param and f_date.year != int(anio_param):
                    continue
            except Exception as e:
                logger.warning(f"API Métricas: Error parseando fecha '{fecha_str}' en factura '{f_id}': {e}")
                if mes_param or anio_param:
                    continue

        total_usd = float(f.get("total_usd", 0) or 0)
        total_abonado = float(f.get("total_abonado", 0) or 0)
        saldo_pendiente = max(0.0, total_usd - total_abonado)

        total_facturado += total_usd
        total_cobrado += total_abonado

        # Estado y distribución
        if saldo_pendiente < TOLERANCIA_SALDO or (total_usd > 0 and total_abonado >= total_usd):
            distribucion["cobrada"] += total_usd
            total_cobradas_monto += total_usd
        elif total_abonado > TOLERANCIA_SALDO:
            distribucion["abonada"] += total_abonado
            distribucion["por_cobrar"] += saldo_pendiente
            total_abonadas_monto += total_abonado
            total_por_cobrar += saldo_pendiente
        else:
            distribucion["por_cobrar"] += total_usd
            total_por_cobrar += total_usd

        # Vencimiento y Aging
        if saldo_pendiente >= TOLERANCIA_SALDO and f_date is not None:
            dias_antiguedad = (hoy - f_date).days
            if dias_antiguedad > DIAS_VENCIMIENTO_DEFAULT:
                vencidas_count += 1
                vencidas_monto += saldo_pendiente

            if dias_antiguedad <= 30:
                aging["rango_0_30"] += saldo_pendiente
            elif dias_antiguedad <= 60:
                aging["rango_31_60"] += saldo_pendiente
            elif dias_antiguedad <= 90:
                aging["rango_61_90"] += saldo_pendiente
            else:
                aging["rango_mas_90"] += saldo_pendiente

        # Top clientes deudores
        if saldo_pendiente >= TOLERANCIA_SALDO:
            cliente_obj = clientes.get(c_id, {})
            nombre_cliente = cliente_obj.get("nombre", f.get("cliente_nombre", f"Cliente {c_id}")) if isinstance(cliente_obj, dict) else f"Cliente {c_id}"
            deuda_por_cliente[nombre_cliente] = deuda_por_cliente.get(nombre_cliente, 0.0) + saldo_pendiente

        # Promedio días de cobro
        pagos = f.get("pagos", [])
        if (saldo_pendiente < TOLERANCIA_SALDO or total_abonado >= total_usd) and f_date and pagos:
            try:
                ultimo_pago = pagos[-1]
                fecha_pago_str = ultimo_pago.get("fecha", "")
                if fecha_pago_str:
                    f_pago_date = datetime.strptime(str(fecha_pago_str)[:10].strip(), "%Y-%m-%d")
                    dias_transcurridos = max(0, (f_pago_date - f_date).days)
                    dias_cobro_lista.append(dias_transcurridos)
            except Exception:
                pass

        # Acumular evolución mensual si la fecha pertenece al rango
        if f_date:
            m_key = f_date.strftime("%Y-%m")
            if m_key in meses_map:
                meses_map[m_key]["facturado"] += total_usd
                meses_map[m_key]["cobrado"] += total_abonado

    # Ordenar Top Clientes por deuda decreciente
    top_clientes_sorted = sorted(deuda_por_cliente.items(), key=lambda x: x[1], reverse=True)[:10]
    top_clientes_labels = [x[0] for x in top_clientes_sorted]
    top_clientes_valores = [round(x[1], 2) for x in top_clientes_sorted]

    # Calcular KPI Tasa de Cobranza y Promedio Días
    tasa_cobranza_pct = round((total_cobrado / total_facturado * 100), 1) if total_facturado > 0 else 100.0
    promedio_dias_cobro = round(sum(dias_cobro_lista) / len(dias_cobro_lista), 1) if dias_cobro_lista else 0.0

    # Construir listas para evolución mensual
    evolucion_labels = []
    evolucion_facturado = []
    evolucion_cobrado = []
    nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    for m_key in sorted(meses_map.keys()):
        yr, mo = m_key.split("-")
        lbl = f"{nombres_meses[int(mo)-1]} {yr[-2:]}"
        evolucion_labels.append(lbl)
        evolucion_facturado.append(round(meses_map[m_key]["facturado"], 2))
        evolucion_cobrado.append(round(meses_map[m_key]["cobrado"], 2))

    return jsonify({
        "success": True,
        "kpis": {
            "total_por_cobrar_usd": round(total_por_cobrar, 2),
            "total_facturado_usd": round(total_facturado, 2),
            "total_cobrado_usd": round(total_cobrado, 2),
            "tasa_cobranza_pct": tasa_cobranza_pct,
            "promedio_dias_cobro": promedio_dias_cobro,
            "vencidas_count": vencidas_count,
            "vencidas_monto_usd": round(vencidas_monto, 2),
        },
        "evolucion_mensual": {
            "labels": evolucion_labels,
            "facturado": evolucion_facturado,
            "cobrado": evolucion_cobrado,
        },
        "distribucion_estado": {
            "por_cobrar": round(distribucion["por_cobrar"], 2),
            "abonada": round(distribucion["abonada"], 2),
            "cobrada": round(distribucion["cobrada"], 2),
        },
        "aging": {
            "rango_0_30": round(aging["rango_0_30"], 2),
            "rango_31_60": round(aging["rango_31_60"], 2),
            "rango_61_90": round(aging["rango_61_90"], 2),
            "rango_mas_90": round(aging["rango_mas_90"], 2),
        },
        "top_clientes": {
            "labels": top_clientes_labels,
            "deuda": top_clientes_valores,
        }
    })



