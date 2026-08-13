# -*- coding: utf-8 -*-
"""
Blueprint para rutas de gestión de la bitácora (/bitacora, /bitacora/limpiar).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.auth_decorators import login_required
from services.bitacora_service import registrar_bitacora

BITACORA_FILE = "bitacora.log"

bitacora_bp = Blueprint("bitacora", __name__)


@bitacora_bp.route("/bitacora")
@login_required
def ver_bitacora():
    """Visualiza los registros de la bitácora con filtros por fecha y por acción."""
    try:
        with open(BITACORA_FILE, "r", encoding="utf-8") as f:
            lineas = f.readlines()
    except Exception:
        lineas = []

    filtro_accion = request.args.get("accion", "").strip()
    filtro_fecha = request.args.get("fecha", "").strip()

    acciones_unicas = set()
    for linea in lineas:
        partes = linea.strip().split("] ", 1)
        if len(partes) == 2:
            resto = partes[1].split(" | ")
            if len(resto) > 1:
                accion = resto[1].replace("Acción: ", "").strip()
                if accion:
                    acciones_unicas.add(accion)

    lineas_filtradas = []
    for linea in lineas:
        partes = linea.strip().split("] ", 1)
        if len(partes) == 2:
            fecha_ok = partes[0][1:11] == filtro_fecha if filtro_fecha else True
            resto = partes[1].split(" | ")
            accion_ok = (resto[1].replace("Acción: ", "").strip() == filtro_accion) if (filtro_accion and len(resto) > 1) else True

            if fecha_ok and accion_ok:
                lineas_filtradas.append(linea)
        else:
            if not filtro_fecha and not filtro_accion:
                lineas_filtradas.append(linea)

    return render_template(
        "bitacora.html",
        lineas=lineas_filtradas,
        acciones_unicas=sorted(acciones_unicas),
        filtro_accion=filtro_accion,
        filtro_fecha=filtro_fecha
    )


@bitacora_bp.route("/bitacora/limpiar", methods=["POST"])
@login_required
def limpiar_bitacora():
    """Limpia el archivo de bitácora registrando primero la acción."""
    try:
        usuario = session.get("usuario", "desconocido")
        registrar_bitacora(usuario, "Limpiar bitácora", "Se limpió toda la bitácora del sistema")
        open(BITACORA_FILE, "w").close()
        flash("Bitácora limpiada exitosamente.", "success")
    except Exception as e:
        flash(f"Error al limpiar la bitácora: {e}", "danger")

    return redirect(url_for("bitacora.ver_bitacora"))
