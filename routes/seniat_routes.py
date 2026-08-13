# -*- coding: utf-8 -*-
"""
Blueprint para rutas de auditoría e integración SENIAT (/seniat/...).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from almacenamiento import cargar_datos
from seguridad_fiscal import seguridad_fiscal
from comunicacion_seniat import comunicador_seniat
from exportacion_seniat import exportador_seniat
from numeracion_fiscal import control_numeracion

ARCHIVO_FACTURAS = "facturas_json/facturas.json"

seniat_bp = Blueprint("seniat", __name__)


@seniat_bp.route("/seniat/consulta")
def seniat_consulta():
    """Interfaz de consulta y handshake de seguridad SENIAT."""
    auth_header = request.headers.get("Authorization")
    seniat_token = request.headers.get("X-SENIAT-Token")

    if not auth_header or not seniat_token:
        return jsonify({
            "error": "Acceso no autorizado - Credenciales SENIAT requeridas",
            "codigo": "AUTH_REQUIRED"
        }), 401

    return jsonify({
        "sistema": "Sistema Fiscal Homologado SENIAT",
        "version": "1.0.0",
        "estado": "ACTIVO",
        "timestamp": datetime.now().isoformat()
    })


@seniat_bp.route("/seniat/facturas/consultar")
def seniat_consultar_facturas():
    """Consulta de documentos inmutables para entes reguladores."""
    try:
        numero = request.args.get("numero")
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}
        resultados = []

        for f in facturas.values():
            if not isinstance(f, dict):
                continue
            if numero and f.get("numero") != numero:
                continue
            if fecha_desde and f.get("fecha", "") < fecha_desde:
                continue
            if fecha_hasta and f.get("fecha", "") > fecha_hasta:
                continue
            resultados.append(f)

        seguridad_fiscal.registrar_log_fiscal(
            usuario="SENIAT",
            accion="CONSULTA_FACTURAS",
            documento_tipo="CONSULTA",
            documento_numero=numero or "MULTIPLE",
            detalles=f"Consulta SENIAT - {len(resultados)} facturas encontradas"
        )

        return jsonify({
            "total_facturas": len(resultados),
            "facturas": resultados,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Error en consulta: {e}", "codigo": "CONSULTA_ERROR"}), 500


@seniat_bp.route("/seniat/exportar/facturas")
def seniat_exportar_facturas():
    """Exporta libros de ventas en formato fiscal SENIAT (CSV/TXT)."""
    try:
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")
        formato = request.args.get("formato", "csv")

        res = exportador_seniat.exportar_facturas(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            formato=formato,
            incluir_metadatos=True
        )

        if res.get("exito"):
            return send_file(res["archivo"], as_attachment=True, download_name=res["nombre_archivo"])
        return jsonify({"error": res.get("mensaje", "Error en exportación")}), 500
    except Exception as e:
        return jsonify({"error": f"Error en exportación: {e}"}), 500


@seniat_bp.route("/seniat/sistema/estado")
def seniat_estado_sistema():
    """Obtiene el estado de salud y estado fiscal del sistema."""
    try:
        estado_num = control_numeracion.obtener_estado_numeracion()
        estado_com = comunicador_seniat.obtener_configuracion_actual()
        facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

        return jsonify({
            "version_sistema": "1.0.0",
            "fecha_consulta": datetime.now().isoformat(),
            "estadisticas": {"total_facturas_emitidas": len(facturas)},
            "numeracion": estado_num,
            "comunicacion_seniat": estado_com
        })
    except Exception as e:
        return jsonify({"error": f"Error consultando estado: {e}"}), 500
