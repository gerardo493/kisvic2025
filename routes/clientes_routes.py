# -*- coding: utf-8 -*-
"""
Blueprint para rutas de gestión de clientes (/clientes, /clientes/nuevo).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.auth_decorators import login_required
from services.bitacora_service import registrar_bitacora
from almacenamiento import cargar_datos, guardar_datos

ARCHIVO_CLIENTES = "clientes.json"
ARCHIVO_FACTURAS = "facturas_json/facturas.json"

clientes_bp = Blueprint("clientes", __name__)



@clientes_bp.route("/clientes")
@login_required
def mostrar_clientes():
    """Muestra el listado de clientes con análisis métrico, segmentación y filtros."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

    q = request.args.get("q", "").strip().lower()
    filtro_orden = request.args.get("orden", "nombre")
    segmento = request.args.get("segmento", "todos")
    estado_pago = request.args.get("estado_pago", "todos")
    fecha_desde = request.args.get("fecha_desde", "")
    fecha_hasta = request.args.get("fecha_hasta", "")

    if q:
        clientes = {k: v for k, v in clientes.items() if q in v.get("nombre", "").lower() or q in k.lower()}

    clientes_analizados = {}
    for id_cliente, cliente in clientes.items():
        facturas_cliente = [f for f in facturas.values() if isinstance(f, dict) and f.get("cliente_id") == id_cliente]
        metrics = _analizar_cliente_metrica(cliente, facturas_cliente)
        clientes_analizados[id_cliente] = metrics

    if segmento != "todos":
        clientes_analizados = {k: v for k, v in clientes_analizados.items() if v["segmento"] == segmento}
    if estado_pago != "todos":
        clientes_analizados = {k: v for k, v in clientes_analizados.items() if v["estado_pago"] == estado_pago}

    # Ordenamiento dinámico según parámetro
    if filtro_orden == "nombre":
        clientes_analizados = dict(sorted(clientes_analizados.items(), key=lambda item: item[1]["cliente"].get("nombre", "").lower()))
    elif filtro_orden == "rif":
        clientes_analizados = dict(sorted(clientes_analizados.items(), key=lambda item: item[0].lower()))
    elif filtro_orden == "total_facturado":
        clientes_analizados = dict(sorted(clientes_analizados.items(), key=lambda item: item[1]["total_facturado"], reverse=True))
    elif filtro_orden == "ultima_compra":
        clientes_analizados = dict(sorted(clientes_analizados.items(), key=lambda item: item[1]["ultima_compra"] or "", reverse=True))

    clientes_final = {k: v["cliente"] for k, v in clientes_analizados.items()}

    clientes_totales = {k: {m: v[m] for m in v if m != "cliente"} for k, v in clientes_analizados.items()}

    return render_template(
        "clientes.html",
        clientes=clientes_final,
        q=q,
        filtro_orden=filtro_orden,
        clientes_totales=clientes_totales,
        segmento=segmento,
        estado_pago=estado_pago,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )


def _analizar_cliente_metrica(cliente: dict, facturas_cliente: list[dict]) -> dict:
    """Helper interno para procesar segmentación y saldo por cobrar del cliente."""
    total_facturado = sum(float(f.get("total_usd", 0)) for f in facturas_cliente)
    total_abonado = sum(float(f.get("total_abonado", 0)) for f in facturas_cliente)
    total_por_cobrar = max(0.0, total_facturado - total_abonado)
    cantidad_facturas = len(facturas_cliente)
    factura_promedio = total_facturado / cantidad_facturas if cantidad_facturas > 0 else 0.0

    fechas = [f.get("fecha", "") for f in facturas_cliente if f.get("fecha")]
    ultima_compra = max(fechas) if fechas else None
    dias_inactivo = 999
    if ultima_compra:
        try:
            dias_inactivo = (datetime.now() - datetime.strptime(ultima_compra, "%Y-%m-%d")).days
        except Exception:
            pass

    segmento = "inactivo"
    if total_facturado > 10000:
        segmento = "vip"
    elif total_facturado > 1000 and dias_inactivo < 90:
        segmento = "frecuente"
    elif total_facturado > 0 and dias_inactivo < 30:
        segmento = "activo"
    elif total_facturado > 0:
        segmento = "regular"

    estado_pago = "al_dia"
    if total_por_cobrar > 0:
        estado_pago = "moroso" if total_por_cobrar > (total_facturado * 0.5) else "pendiente"

    return {
        "cliente": cliente,
        "total_facturado": total_facturado,
        "total_abonado": total_abonado,
        "total_por_cobrar": total_por_cobrar,
        "cantidad_facturas": cantidad_facturas,
        "factura_promedio": factura_promedio,
        "ultima_compra": ultima_compra,
        "dias_inactivo": dias_inactivo,
        "segmento": segmento,
        "estado_pago": estado_pago,
    }


@clientes_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_cliente():
    """Creación de cliente con validaciones basales SENIAT, Persona de Contacto y Geocodificación."""
    if request.method == "POST":
        try:
            clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
            tipo_id = request.form.get("tipo_id", "").strip().upper()
            numero_id = request.form.get("numero_id", "").strip()
            digito_verificador = request.form.get("digito_verificador", "").strip()
            nombre = request.form.get("nombre", "").strip().upper()
            email = request.form.get("email", "").strip().lower()
            codigo_pais = request.form.get("codigo_pais", "+58").strip()
            telefono_num = request.form.get("telefono", "").strip()
            telefono = f"{codigo_pais}{telefono_num}" if telefono_num else ""
            direccion = request.form.get("direccion", "").strip()
            estado = request.form.get("estado", "").strip()
            municipio = request.form.get("municipio", "").strip()

            if not estado:
                est_inf, mun_inf = detectar_estado_municipio(direccion)
                estado = estado or est_inf
                municipio = municipio or mun_inf

            latitud, longitud = geocodificar_direccion(direccion, municipio, estado)

            # Persona de Contacto
            contacto_nombre = request.form.get("contacto_nombre", "").strip()
            contacto_cargo = request.form.get("contacto_cargo", "").strip()
            contacto_codigo_pais = request.form.get("contacto_codigo_pais", "+58").strip()
            contacto_telefono_num = request.form.get("contacto_telefono", "").strip()
            contacto_telefono = f"{contacto_codigo_pais}{contacto_telefono_num}" if contacto_telefono_num else ""
            contacto_email = request.form.get("contacto_email", "").strip().lower()

            contacto_obj = {
                "nombre": contacto_nombre,
                "cargo": contacto_cargo,
                "codigo_pais": contacto_codigo_pais,
                "telefono": contacto_telefono,
                "email": contacto_email
            }

            # Términos de Crédito
            try:
                limite_credito = float(request.form.get("limite_credito", 0) or 0)
            except (ValueError, TypeError):
                limite_credito = 0.0

            try:
                dias_credito = int(request.form.get("dias_credito", 0) or 0)
            except (ValueError, TypeError):
                dias_credito = 0

            if tipo_id in ["J", "P", "G"] and digito_verificador:
                id_cliente = f"{tipo_id}-{numero_id}-{digito_verificador}"
            else:
                id_cliente = f"{tipo_id}-{numero_id}"

            if id_cliente in clientes:
                flash(f"El cliente con identificación {id_cliente} ya existe", "warning")
                return render_template("cliente_form.html")

            clientes[id_cliente] = {
                "id": id_cliente,
                "rif": id_cliente,
                "tipo_id": tipo_id,
                "numero_id": numero_id,
                "digito_verificador": digito_verificador,
                "nombre": nombre,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "estado": estado,
                "municipio": municipio,
                "latitud": latitud,
                "longitud": longitud,
                "contacto": contacto_obj,
                "limite_credito": limite_credito,
                "dias_credito": dias_credito,
                "validado_seniat": True,
                "fecha_registro": datetime.now().strftime("%Y-%m-%d")
            }
            guardar_datos(ARCHIVO_CLIENTES, clientes)
            registrar_bitacora(session.get("usuario", "admin"), "Nuevo cliente", f"Cliente creado: {id_cliente}")
            flash("Cliente registrado exitosamente con geocodificación comercial", "success")
            return redirect(url_for("clientes.mostrar_clientes"))
        except Exception as e:
            flash(f"Error registrando cliente: {e}", "danger")

    return render_template("cliente_form.html")


@clientes_bp.route("/clientes/<path:id>/editar", methods=["GET", "POST"])
@login_required
def editar_cliente(id: str):
    """Formulario para editar un cliente existente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    if id not in clientes:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for("clientes.mostrar_clientes"))

    if request.method == "POST":
        try:
            nombre = request.form.get("nombre", "").strip().upper()
            email = request.form.get("email", "").strip().lower()
            codigo_pais = request.form.get("codigo_pais", "+58").strip()
            telefono_num = request.form.get("telefono", "").strip()
            telefono = f"{codigo_pais}{telefono_num}" if telefono_num else ""
            direccion = request.form.get("direccion", "").strip()
            estado = request.form.get("estado", "").strip()
            municipio = request.form.get("municipio", "").strip()

            if not estado:
                est_inf, mun_inf = detectar_estado_municipio(direccion)
                estado = estado or est_inf
                municipio = municipio or mun_inf

            latitud, longitud = geocodificar_direccion(direccion, municipio, estado)

            # Persona de Contacto
            contacto_nombre = request.form.get("contacto_nombre", "").strip()
            contacto_cargo = request.form.get("contacto_cargo", "").strip()
            contacto_codigo_pais = request.form.get("contacto_codigo_pais", "+58").strip()
            contacto_telefono_num = request.form.get("contacto_telefono", "").strip()
            contacto_telefono = f"{contacto_codigo_pais}{contacto_telefono_num}" if contacto_telefono_num else ""
            contacto_email = request.form.get("contacto_email", "").strip().lower()

            contacto_obj = {
                "nombre": contacto_nombre,
                "cargo": contacto_cargo,
                "codigo_pais": contacto_codigo_pais,
                "telefono": contacto_telefono,
                "email": contacto_email
            }

            # Términos de Crédito
            try:
                limite_credito = float(request.form.get("limite_credito", 0) or 0)
            except (ValueError, TypeError):
                limite_credito = 0.0

            try:
                dias_credito = int(request.form.get("dias_credito", 0) or 0)
            except (ValueError, TypeError):
                dias_credito = 0

            clientes[id].update({
                "nombre": nombre,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "estado": estado,
                "municipio": municipio,
                "latitud": latitud,
                "longitud": longitud,
                "contacto": contacto_obj,
                "limite_credito": limite_credito,
                "dias_credito": dias_credito,
                "fecha_actualizacion": datetime.now().isoformat()
            })
            if guardar_datos(ARCHIVO_CLIENTES, clientes):
                registrar_bitacora(session.get("usuario", "admin"), "Editar cliente", f"Cliente {id} actualizado")
                flash(f"Cliente {id} actualizado exitosamente", "success")
                return redirect(url_for("clientes.mostrar_clientes"))
        except Exception as e:
            flash(f"Error al actualizar cliente: {e}", "danger")

    return render_template("cliente_form.html", cliente=clientes[id])


@clientes_bp.route("/clientes/dashboard")
@login_required
def dashboard_clientes():
    """Dashboard de analítica e indicadores clave de clientes."""
    try:
        clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
        facturas = cargar_datos(ARCHIVO_FACTURAS, crear_vacio=False) or {}

        periodo = request.args.get("periodo", "6")
        segmento_filtro = request.args.get("segmento", "todos")
        estado_filtro = request.args.get("estado", "todos")
        vista_tipo = request.args.get("vista", "resumen")

        # Analizar métricas de cada cliente
        clientes_analizados = []
        for cid, c in clientes.items():
            facturas_cliente = [f for f in facturas.values() if isinstance(f, dict) and f.get("cliente_id") == cid]
            datos_m = _analizar_cliente_metrica(c, facturas_cliente)
            datos_m['id'] = c.get('id') or cid
            datos_m['nombre'] = c.get('nombre', 'Sin nombre')
            clientes_analizados.append(datos_m)

        # Aplicar filtros si existen
        if segmento_filtro != 'todos':
            clientes_analizados = [c for c in clientes_analizados if c.get('segmento') == segmento_filtro]
        if estado_filtro != 'todos':
            clientes_analizados = [c for c in clientes_analizados if c.get('estado_pago') == estado_filtro]

        # Calcular consolidados
        total_clientes = len(clientes_analizados)
        total_facturado = sum(c['total_facturado'] for c in clientes_analizados)
        total_abonado = sum(c['total_abonado'] for c in clientes_analizados)
        total_por_cobrar = sum(c['total_por_cobrar'] for c in clientes_analizados)

        # Segmentos
        segmentos = {
            'vip': {'clientes': 0, 'facturado': 0.0, 'color': '#FFD700', 'porcentaje': 0.0},
            'frecuente': {'clientes': 0, 'facturado': 0.0, 'color': '#32CD32', 'porcentaje': 0.0},
            'activo': {'clientes': 0, 'facturado': 0.0, 'color': '#1E90FF', 'porcentaje': 0.0},
            'regular': {'clientes': 0, 'facturado': 0.0, 'color': '#FFA500', 'porcentaje': 0.0},
            'inactivo': {'clientes': 0, 'facturado': 0.0, 'color': '#DC143C', 'porcentaje': 0.0},
            'potencial': {'clientes': 0, 'facturado': 0.0, 'color': '#9370DB', 'porcentaje': 0.0}
        }

        # Estados de pago
        estados_pago = {
            'al_dia': {'clientes': 0, 'monto': 0.0},
            'pendiente': {'clientes': 0, 'monto': 0.0},
            'moroso': {'clientes': 0, 'monto': 0.0}
        }

        for c in clientes_analizados:
            seg = c.get('segmento', 'potencial')
            if seg in segmentos:
                segmentos[seg]['clientes'] += 1
                segmentos[seg]['facturado'] += c.get('total_facturado', 0.0)

            est = c.get('estado_pago', 'al_dia')
            if est in estados_pago:
                estados_pago[est]['clientes'] += 1
                estados_pago[est]['monto'] += c.get('total_por_cobrar', 0.0)

        # Porcentajes de segmentos
        for seg, data in segmentos.items():
            if total_clientes > 0:
                data['porcentaje'] = round((data['clientes'] / total_clientes) * 100, 1)

        # Top 10 Clientes por facturación
        clientes_top = sorted(clientes_analizados, key=lambda x: x['total_facturado'], reverse=True)[:10]

        # Tendencias de facturación por mes (últimos 6 meses)
        tendencias_dict = {}
        for f in facturas.values():
            if isinstance(f, dict):
                fecha = f.get('fecha', '')
                if len(fecha) >= 7:
                    mes = fecha[:7]  # YYYY-MM
                    tendencias_dict[mes] = tendencias_dict.get(mes, {'facturado': 0.0, 'clientes': set()})
                    tendencias_dict[mes]['facturado'] += float(f.get('total_usd', 0) or 0)
                    if f.get('cliente_id'):
                        tendencias_dict[mes]['clientes'].add(f.get('cliente_id'))

        tendencias = []
        for mes in sorted(tendencias_dict.keys())[-6:]:
            tendencias.append({
                'mes': mes,
                'facturado': round(tendencias_dict[mes]['facturado'], 2),
                'clientes': len(tendencias_dict[mes]['clientes'])
            })

        if not tendencias:
            now_str = datetime.now().strftime("%Y-%m")
            tendencias = [{'mes': now_str, 'facturado': 0.0, 'clientes': 0}]

        return render_template(
            "dashboard_clientes.html",
            total_clientes=total_clientes,
            total_facturado=total_facturado,
            total_abonado=total_abonado,
            total_por_cobrar=total_por_cobrar,
            segmentos=segmentos,
            estados_pago=estados_pago,
            clientes_top=clientes_top,
            tendencias=tendencias,
            periodo=periodo,
            segmento_filtro=segmento_filtro,
            estado_filtro=estado_filtro,
            vista_tipo=vista_tipo
        )
    except Exception as e:
        flash(f"Error al cargar el dashboard de clientes: {e}", "danger")
        return redirect(url_for("clientes.mostrar_clientes"))


@clientes_bp.route("/clientes/<path:id>/eliminar", methods=["POST"])
@login_required
def eliminar_cliente(id: str):
    """Elimina un cliente del sistema."""
    clientes = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False) or {}
    if id in clientes:
        del clientes[id]
        if guardar_datos(ARCHIVO_CLIENTES, clientes):
            registrar_bitacora(session.get("usuario", "admin"), "Eliminar cliente", f"ID: {id}")
            flash("Cliente eliminado exitosamente", "success")
        else:
            flash("Error al eliminar el cliente", "danger")
    else:
        flash("Cliente no encontrado", "danger")
    return redirect(url_for("clientes.mostrar_clientes"))



