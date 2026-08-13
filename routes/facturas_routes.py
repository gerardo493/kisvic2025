# -*- coding: utf-8 -*-
"""
Blueprint para rutas de facturación (/facturas, /facturas/<id>).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from utils.auth_decorators import login_required
from almacenamiento import cargar_datos, guardar_datos
from services.factura_creacion_service import procesar_nueva_factura
from services.pagos_service import registrar_abono_factura
from services.bcv_service import obtener_tasa_bcv

ARCHIVO_FACTURAS = "facturas_json/facturas.json"
ARCHIVO_CLIENTES = "clientes.json"

facturas_bp = Blueprint("facturas", __name__)


@facturas_bp.route("/facturas")
@login_required
def mostrar_facturas():
    """Muestra el listado de facturas con filtros, estados calculados y totales."""
    facturas = _cargar_todas_las_facturas()
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}

    q_search = request.args.get("search", "").strip().lower()
    q_cliente = request.args.get("cliente", "").strip().lower()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    filtro_estado = request.args.get("estado", "todas").strip().lower()
    sort_by = request.args.get("sort", "numero").strip().lower()
    order = request.args.get("order", "desc").strip().lower()

    tasa_bcv = obtener_tasa_bcv() or 36.00

    facturas_procesadas = {}
    for f_id, f in facturas.items():
        if not isinstance(f, dict) or not f_id:
            continue
        facturas_procesadas[f_id] = _normalizar_factura(f)

    filtradas_list = []
    total_usd_sum = 0.0
    total_bs_sum = 0.0

    for f_id, f in facturas_procesadas.items():
        numero = str(f.get("numero", f_id)).lower()
        if q_search and q_search not in numero:
            continue

        c_id = str(f.get("cliente_id", ""))
        c_obj = clientes.get(c_id, {})
        c_nombre = (c_obj.get("nombre", "") if isinstance(c_obj, dict) else "").lower()
        c_rif = (c_obj.get("rif", "") if isinstance(c_obj, dict) else "").lower()

        if q_cliente and (q_cliente not in c_nombre and q_cliente not in c_rif and q_cliente not in c_id.lower()):
            continue

        fecha_str = f.get("fecha", "")
        if fecha_desde and fecha_str < fecha_desde:
            continue
        if fecha_hasta and fecha_str > fecha_hasta:
            continue

        est = str(f.get("estado", "")).lower()
        if filtro_estado != "todas" and est != filtro_estado:
            continue

        tot_usd = float(f.get("total_usd", 0) or 0)
        tot_bs = float(f.get("total_bs", 0) or (tot_usd * tasa_bcv))

        total_usd_sum += tot_usd
        total_bs_sum += tot_bs

        filtradas_list.append((f_id, f))

    reverse = (order == "desc")
    if sort_by == "fecha":
        filtradas_list.sort(key=lambda x: str(x[1].get("fecha", "")), reverse=reverse)
    elif sort_by == "cliente":
        filtradas_list.sort(key=lambda x: str(x[1].get("cliente_id", "")), reverse=reverse)
    elif sort_by == "total_usd":
        filtradas_list.sort(key=lambda x: float(x[1].get("total_usd", 0) or 0), reverse=reverse)
    elif sort_by == "total_bs":
        filtradas_list.sort(key=lambda x: float(x[1].get("total_bs", 0) or 0), reverse=reverse)
    elif sort_by == "estado":
        filtradas_list.sort(key=lambda x: str(x[1].get("estado", "")), reverse=reverse)
    else:
        filtradas_list.sort(key=lambda x: str(x[1].get("numero", x[0])), reverse=reverse)

    return render_template(
        "facturas.html",
        rows=filtradas_list,
        facturas=facturas_procesadas,
        clientes=clientes,
        total_usd_sum=total_usd_sum,
        total_bs_sum=total_bs_sum,
        filtro_estado=filtro_estado,
        tasa_bcv=tasa_bcv,
        sort=sort_by,
        order=order
    )



@facturas_bp.route("/facturas/<id>")
@login_required
def ver_factura(id: str):
    """Muestra el detalle individual de una factura especificada."""
    if not id or str(id).strip() == "":
        flash("ID de factura inválido", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    facturas = _cargar_todas_las_facturas()
    real_id, factura_raw = _buscar_factura(facturas, id)
    if not factura_raw:
        flash("Factura no encontrada", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    factura = _normalizar_factura(factura_raw)
    if not factura.get("id"):
        factura["id"] = real_id or id

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    cliente = clientes.get(factura.get("cliente_id"), {})
    inventario = cargar_datos("inventario.json", crear_vacio=False) or {}
    empresa = _obtener_empresa()

    return render_template(
        "factura_detalle.html",
        factura=factura,
        cliente=cliente,
        clientes=clientes,
        inventario=inventario,
        id=real_id or id,
        empresa=empresa
    )


@facturas_bp.route("/facturas/nueva", methods=["GET", "POST"])
@login_required
def nueva_factura():
    """Ruta para emisión de nuevas facturas con validación fiscal SENIAT."""
    if request.method == "POST":
        try:
            usuario_actual = session.get("usuario", "SISTEMA")
            factura_data, factura_id = procesar_nueva_factura(request.form, usuario_actual)

            factura_data["id"] = factura_id
            numero_fiscal = str(factura_data.get("numero", "")).strip()

            facturas = _cargar_todas_las_facturas()
            facturas[factura_id] = factura_data
            if numero_fiscal:
                facturas[numero_fiscal] = factura_data

            guardar_datos(ARCHIVO_FACTURAS, facturas)

            facturas_dir = "facturas_json"
            os.makedirs(facturas_dir, exist_ok=True)
            guardar_datos(os.path.join(facturas_dir, f"factura_{factura_id}.json"), factura_data)
            if numero_fiscal and numero_fiscal != factura_id:
                guardar_datos(os.path.join(facturas_dir, f"factura_{numero_fiscal}.json"), factura_data)

            flash(f"Factura N° {numero_fiscal or factura_id} creada exitosamente", "success")
            return redirect(url_for("facturas.mostrar_facturas"))
        except Exception as e:
            flash(f"Error procesando factura: {e}", "danger")

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    inventario = cargar_datos("inventario.json", crear_vacio=False) or {}
    tasa_bcv = obtener_tasa_bcv() or 36.00

    return render_template(
        "factura_form.html",
        clientes=clientes,
        inventario=inventario,
        tasa_bcv=tasa_bcv,
        fecha_actual=datetime.now().strftime("%Y-%m-%d"),
        factura=None,
        editar=False,
        zip=zip
    )


@facturas_bp.route("/facturas/<id>/registrar_pago", methods=["GET", "POST"])
@login_required
def registrar_pago(id: str):
    """Permite ver la pantalla de registro de pago (GET) o procesar el abono (POST) sobre la factura especificada."""
    if not id or str(id).strip() == "":
        flash("ID de factura inválido", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    facturas = _cargar_todas_las_facturas()
    real_id, factura_raw = _buscar_factura(facturas, id)
    if not factura_raw:
        flash("Factura no encontrada", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    target_key = real_id or id
    factura = _normalizar_factura(factura_raw)

    if request.method == "GET":
        clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
        cliente = clientes.get(str(factura.get("cliente_id", "")), {})
        if not isinstance(cliente, dict) or not cliente.get("nombre"):
            cliente = {
                "nombre": str(factura.get("cliente_nombre") or factura.get("cliente_id") or "Cliente Registrado"),
                "rif": str(factura.get("cliente_rif") or "")
            }

        saldo_pendiente = float(factura.get("saldo_pendiente", factura.get("total_usd", 0)))
        tasa_bcv = obtener_tasa_bcv() or 36.00

        return render_template(
            "registrar_pago.html",
            factura=factura,
            cliente=cliente,
            saldo_pendiente=saldo_pendiente,
            tasa_bcv=tasa_bcv,
            id=target_key
        )

    monto = float(request.form.get("monto_pago", 0) or 0)
    if monto <= 0:
        flash("El monto del pago debe ser mayor a $0.00", "danger")
        return redirect(url_for("facturas.registrar_pago", id=target_key))

    factura_actualizada, _ = registrar_abono_factura(
        factura=factura_raw,
        monto_pago=monto,
        moneda_pago=request.form.get("moneda_pago", "USD"),
        metodo_pago=request.form.get("metodo_pago", ""),
        referencia_pago=request.form.get("referencia_pago", ""),
        banco=request.form.get("banco", "")
    )

    facturas[target_key] = factura_actualizada
    num_fiscal = str(factura_actualizada.get("numero", "")).strip()
    if num_fiscal:
        facturas[num_fiscal] = factura_actualizada

    guardar_datos(ARCHIVO_FACTURAS, facturas)

    facturas_dir = "facturas_json"
    os.makedirs(facturas_dir, exist_ok=True)
    guardar_datos(os.path.join(facturas_dir, f"factura_{target_key}.json"), factura_actualizada)
    if num_fiscal and num_fiscal != target_key:
        guardar_datos(os.path.join(facturas_dir, f"factura_{num_fiscal}.json"), factura_actualizada)

    flash("Pago registrado exitosamente", "success")
    return redirect(url_for("facturas.ver_factura", id=target_key))


def _normalizar_factura(factura: dict) -> dict:
    """Helper interno para estructurar subtotales, abonados y estado financiero de la factura."""
    f = factura.copy()
    precios_raw = f.get("precios", [])
    precios = []
    for p in precios_raw:
        try:
            precios.append(float(p))
        except (ValueError, TypeError):
            precios.append(0.0)

    cantidades_raw = f.get("cantidades", [])
    cantidades = []
    for c in cantidades_raw:
        try:
            cantidades.append(int(c))
        except (ValueError, TypeError):
            cantidades.append(0)

    subtotal = sum(
        precios[i] * cantidades[i]
        for i in range(min(len(precios), len(cantidades)))
    ) if (precios and cantidades) else 0.0

    tasa_bcv = float(f.get("tasa_bcv", 1.0) or 1.0)
    descuento = float(f.get("descuento_total", 0) or 0)
    iva = float(f.get("iva_total", 0) or 0)

    total_usd = float(f.get("total_usd") or (subtotal - descuento + iva) or 0.0)
    total_bs = float(f.get("total_bs") or (total_usd * tasa_bcv))

    total_abonado = sum(
        float(p.get("monto", 0)) for p in f.get("pagos", [])
        if isinstance(p, dict) and p.get("monto")
    )
    saldo_pendiente = max(0.0, total_usd - total_abonado)

    estado = f.get("estado", "")
    if not estado or estado == "cobrada":
        if saldo_pendiente < 0.01 or total_abonado >= total_usd:
            estado = "pagada"
        elif total_abonado > 0:
            estado = "abonada"
        else:
            estado = "pendiente"

    f.update({
        "id": f.get("id", ""),
        "subtotal_usd": f.get("subtotal_usd", subtotal),
        "subtotal_bs": f.get("subtotal_bs", subtotal * tasa_bcv),
        "descuento_total": descuento,
        "iva_total": iva,
        "total_usd": total_usd,
        "total_bs": total_bs,
        "total_abonado": total_abonado,
        "saldo_pendiente": saldo_pendiente,
        "estado": estado,
        "pagos": f.get("pagos", []),
        "productos": f.get("productos", []),
        "cantidades": cantidades,
        "precios": precios
    })
    return f


@facturas_bp.route("/facturas/<id>/imprimir")
@login_required
def imprimir_factura(id: str):
    """Genera la plantilla o vista imprimible para la factura."""
    facturas = _cargar_todas_las_facturas()
    real_id, factura_raw = _buscar_factura(facturas, id)
    if not factura_raw:
        flash("Factura no encontrada", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    factura = _normalizar_factura(factura_raw)
    if not factura.get("id"):
        factura["id"] = real_id or id

    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    cliente = clientes.get(factura.get("cliente_id"), {})
    inventario = cargar_datos("inventario.json", crear_vacio=False) or {}
    empresa = _obtener_empresa()
    return render_template(
        "factura_imprimir.html",
        factura=factura,
        cliente=cliente,
        clientes=clientes,
        inventario=inventario,
        id=real_id or id,
        empresa=empresa
    )


def _obtener_empresa() -> dict:
    data = cargar_datos("empresa.json", crear_vacio=False)
    if data and isinstance(data, dict):
        return data
    return {
        "nombre": "Nombre de la Empresa",
        "rif": "J-000000000",
        "telefono": "0000-0000000",
        "direccion": "Dirección de la empresa"
    }


def _cargar_todas_las_facturas() -> dict:
    """Carga todas las facturas deduplicadas por ID/Número desde facturas.json e incluye los archivos individuales factura_*.json."""
    raw_facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}
    if not isinstance(raw_facturas, dict):
        raw_facturas = {}

    facturas_dir = "facturas_json"
    if os.path.exists(facturas_dir):
        for fname in os.listdir(facturas_dir):
            if fname.endswith(".json") and fname != "facturas.json":
                f_key = fname[len("factura_"):-len(".json")] if fname.startswith("factura_") else fname[:-len(".json")]
                if f_key not in raw_facturas:
                    fdata = cargar_datos(os.path.join(facturas_dir, fname), crear_vacio=False)
                    if fdata and isinstance(fdata, dict):
                        raw_facturas[f_key] = fdata

    # Deduplicación: 1 sola entrada por factura real
    facturas_deduplicadas = {}
    vistos = set()

    for key, f in raw_facturas.items():
        if not isinstance(f, dict):
            continue
        if str(key).strip().lower() in ("facturas", "facturas_json", "none", "null", ""):
            continue
        if str(f.get("id", "")).strip().lower() in ("facturas", "none", "null", "") and not f.get("numero"):
            continue
        num = str(f.get("numero", "")).strip()
        f_id = str(f.get("id", "")).strip()
        num_sec = str(f.get("numero_secuencial", "")).strip()

        unique_key = num or f_id or num_sec or str(key).strip()

        if unique_key in vistos:
            continue
        vistos.add(unique_key)

        primary_key = f_id or str(key).strip() or num
        facturas_deduplicadas[primary_key] = f

    return facturas_deduplicadas


def _buscar_factura(facturas: dict, target_id: str) -> tuple[str | None, dict | None]:
    """Busca una factura por clave, id, número fiscal o secuencial de forma flexible."""
    if not target_id or not isinstance(facturas, dict):
        return None, None

    t_str = str(target_id).strip()
    t_lower = t_str.lower()

    if t_str in facturas and isinstance(facturas[t_str], dict):
        return t_str, facturas[t_str]
    if t_lower in facturas and isinstance(facturas[t_lower], dict):
        return t_lower, facturas[t_lower]

    for k, f in facturas.items():
        if not isinstance(f, dict):
            continue

        f_num = str(f.get("numero", "")).strip().lower()
        f_id = str(f.get("id", "")).strip().lower()
        f_sec = str(f.get("numero_secuencial", "")).strip().lower()
        k_str = str(k).strip().lower()

        if t_lower in (f_num, f_id, f_sec, k_str):
            return str(k), f

        t_clean = t_lower.replace("fac-", "").replace("factura_", "").lstrip("0")
        f_num_clean = f_num.replace("fac-", "").lstrip("0")
        f_sec_clean = f_sec.lstrip("0")
        k_clean = k_str.replace("fac-", "").replace("factura_", "").lstrip("0")

        if t_clean and (t_clean == f_num_clean or t_clean == f_sec_clean or t_clean == k_clean):
            return str(k), f

    return None, None


@facturas_bp.route("/facturas/<id>/eliminar", methods=["POST"])
@login_required
def eliminar_factura_bp(id: str):
    """Elimina una factura removiendo referencias y archivos en disco."""
    if not id or str(id).strip() == "":
        flash("ID de factura inválido", "danger")
        return redirect(url_for("facturas.mostrar_facturas"))

    facturas = _cargar_todas_las_facturas()
    real_id, f_raw = _buscar_factura(facturas, id)

    keys_to_remove = set()
    if f_raw:
        if f_raw.get("id"): keys_to_remove.add(str(f_raw.get("id")))
        if f_raw.get("numero"): keys_to_remove.add(str(f_raw.get("numero")))
        if f_raw.get("numero_secuencial"): keys_to_remove.add(str(f_raw.get("numero_secuencial")))
    if real_id: keys_to_remove.add(str(real_id))
    keys_to_remove.add(str(id))

    # Cargar maestro completo sin filtrar
    base_facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}
    for k in list(base_facturas.keys()):
        f = base_facturas[k]
        if isinstance(f, dict):
            if str(k) in keys_to_remove or str(f.get("numero")) in keys_to_remove or str(f.get("id")) in keys_to_remove:
                base_facturas.pop(k, None)

    for k in keys_to_remove:
        base_facturas.pop(k, None)

    guardar_datos(ARCHIVO_FACTURAS, base_facturas)

    # Eliminar archivos individuales de disco
    facturas_dir = "facturas_json"
    if os.path.exists(facturas_dir):
        for k in keys_to_remove:
            if not k: continue
            for fname in [f"factura_{k}.json", f"{k}.json"]:
                pfile = os.path.join(facturas_dir, fname)
                if os.path.exists(pfile):
                    try:
                        os.remove(pfile)
                    except Exception as e:
                        print(f"Error borrando archivo {pfile}: {e}")

    flash("Factura eliminada exitosamente", "success")
    return redirect(url_for("facturas.mostrar_facturas"))




