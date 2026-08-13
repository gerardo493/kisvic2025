# -*- coding: utf-8 -*-
"""
Blueprint para rutas de cotizaciones (/cotizaciones).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.auth_decorators import login_required
from almacenamiento import cargar_datos, guardar_datos

ARCHIVO_CLIENTES = "clientes.json"
COTIZACIONES_DIR = "cotizaciones_json"

cotizaciones_bp = Blueprint("cotizaciones", __name__)


@cotizaciones_bp.route("/cotizaciones")
@login_required
def mostrar_cotizaciones():
    """Muestra la lista de cotizaciones activas registradas en el sistema."""
    cotizaciones = {}

    if not os.path.exists(COTIZACIONES_DIR):
        os.makedirs(COTIZACIONES_DIR, exist_ok=True)
        clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
        return render_template(
            "cotizaciones.html",
            cotizaciones={},
            clientes=clientes,
            now=datetime.now().strftime("%Y-%m-%d")
        )

    for filename in os.listdir(COTIZACIONES_DIR):
        if not filename.startswith("cotizacion_") or not filename.endswith(".json"):
            continue
        try:
            filepath = os.path.join(COTIZACIONES_DIR, filename)
            cot_data = cargar_datos(filepath, crear_vacio=False)
            if not cot_data:
                continue

            cot_id = filename[len("cotizacion_"):-len(".json")]
            fecha = cot_data.get("fecha", "")
            validez_dias = int(cot_data.get("validez_dias", cot_data.get("validez", 30)))

            try:
                validez = (datetime.strptime(fecha, "%Y-%m-%d") + timedelta(days=validez_dias)).strftime("%Y-%m-%d")
            except Exception:
                validez = (datetime.now() + timedelta(days=validez_dias)).strftime("%Y-%m-%d")

            cliente = cot_data.get("cliente", {})
            cliente_id = cliente.get("id") or cot_data.get("cliente_id", "")
            total_raw = cot_data.get("total_usd", 0)
            total = f"${float(total_raw):.2f}" if isinstance(total_raw, (int, float)) else str(total_raw)

            cotizaciones[cot_id] = {
                "numero": cot_data.get("numero_cotizacion", cot_id),
                "fecha": fecha,
                "hora": cot_data.get("hora", "--:--"),
                "cliente_id": cliente_id,
                "total": total,
                "validez": validez
            }
        except Exception as e:
            print(f"Error procesando cotización {filename}: {e}")

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    return render_template(
        "cotizaciones.html",
        cotizaciones=cotizaciones,
        clientes=clientes,
        now=datetime.now().strftime("%Y-%m-%d")
    )


@cotizaciones_bp.route("/cotizaciones/nueva", methods=["GET", "POST"])
@login_required
def nueva_cotizacion():
    """Ruta para la emisión de nuevas cotizaciones."""
    if request.method == "POST":
        try:
            cliente_id = request.form.get("cliente_id", "").strip()
            fecha = request.form.get("fecha", datetime.now().strftime("%Y-%m-%d")).strip()
            validez_dias = int(request.form.get("validez_dias", 30))

            productos = request.form.getlist("productos[]")
            cantidades = request.form.getlist("cantidades[]")
            precios = [float(p) for p in request.form.getlist("precios[]") if p]

            subtotal_usd = sum(precios[i] * int(cantidades[i]) for i in range(min(len(precios), len(cantidades))))
            tasa_bcv = float(request.form.get("tasa_bcv", 36.0) or 36.0)
            total_bs = subtotal_usd * tasa_bcv

            cot_id = str(int(datetime.now().timestamp()))
            payload = {
                "numero_cotizacion": f"COT-{cot_id}",
                "cliente_id": cliente_id,
                "fecha": fecha,
                "validez_dias": validez_dias,
                "productos": productos,
                "cantidades": cantidades,
                "precios": precios,
                "tasa_bcv": tasa_bcv,
                "total_usd": subtotal_usd,
                "total_bs": total_bs,
                "fecha_creacion": datetime.now().isoformat()
            }

            os.makedirs(COTIZACIONES_DIR, exist_ok=True)
            filepath = os.path.join(COTIZACIONES_DIR, f"cotizacion_{cot_id}.json")
            if guardar_datos(filepath, payload):
                flash("Cotización creada exitosamente", "success")
                return redirect(url_for("cotizaciones.mostrar_cotizaciones"))
            else:
                flash("Error al guardar la cotización", "danger")
        except Exception as e:
            flash(f"Error procesando cotización: {e}", "danger")

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    inventario = cargar_datos("inventario.json", crear_vacio=False) or {}
    return render_template("cotizacion_form.html", clientes=clientes, inventario=inventario)


@cotizaciones_bp.route("/cotizaciones/<id>/imprimir")
@login_required
def imprimir_cotizacion(id: str):
    """Vista imprimible de una cotización especificada."""
    filepath = os.path.join(COTIZACIONES_DIR, f"cotizacion_{id}.json")
    if not os.path.exists(filepath):
        flash("Cotización no encontrada", "danger")
        return redirect(url_for("cotizaciones.mostrar_cotizaciones"))

    cot_data = cargar_datos(filepath, crear_vacio=False) or {}
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    cliente = clientes.get(cot_data.get("cliente_id"), {})
    return render_template("cotizacion_imprimir.html", cotizacion=cot_data, cliente=cliente, id=id)


