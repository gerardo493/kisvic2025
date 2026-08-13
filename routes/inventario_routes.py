# -*- coding: utf-8 -*-
"""
Blueprint para rutas de gestión de inventario (/inventario, /inventario/nuevo).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.auth_decorators import login_required
from almacenamiento import cargar_datos, guardar_datos
from services.inventario_service import calcular_metricas_inventario

ARCHIVO_INVENTARIO = "inventario.json"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGENES_PRODUCTOS_FOLDER = os.path.join(BASE_DIR, "static", "imagenes_productos")

inventario_bp = Blueprint("inventario", __name__)


@inventario_bp.route("/inventario")
@login_required
def mostrar_inventario():
    """Listado y filtrado avanzado del inventario del sistema."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    q = request.args.get("q", "").strip().lower()
    filtro_categoria = request.args.get("categoria", "").strip()
    filtro_orden = request.args.get("orden", "nombre")
    filtro_stock = request.args.get("stock", "todos")
    vista_tipo = request.args.get("vista", "tabla")

    categorias = sorted(list({
        p.get("categoria") for p in inventario.values()
        if isinstance(p, dict) and p.get("categoria")
    }))

    productos_filtrados = {}
    alertas_stock = []

    for p_id, producto in inventario.items():
        if not isinstance(producto, dict):
            continue
        nombre = producto.get("nombre", "")
        codigo = producto.get("codigo", "")

        if q and q not in nombre.lower() and q not in codigo.lower():
            continue
        if filtro_categoria and producto.get("categoria") != filtro_categoria:
            continue

        cantidad = int(float(producto.get("cantidad", 0) or 0))
        stock_minimo = int(float(producto.get("stock_minimo", 5) or 5))

        if cantidad <= 0:
            alertas_stock.append({"id": p_id, "nombre": nombre, "cantidad": cantidad, "tipo": "agotado"})
        elif cantidad <= stock_minimo:
            alertas_stock.append({"id": p_id, "nombre": nombre, "cantidad": cantidad, "stock_minimo": stock_minimo, "tipo": "bajo"})

        if (filtro_stock == "bajo" and cantidad > stock_minimo) or \
           (filtro_stock == "agotado" and cantidad > 0) or \
           (filtro_stock == "disponible" and cantidad <= 0):
            continue

        productos_filtrados[p_id] = producto

    valor_total = sum(
        float(p.get("precio", 0) or 0) * int(float(p.get("cantidad", 0) or 0))
        for p in inventario.values() if isinstance(p, dict)
    )

    return render_template(
        "inventario.html",
        inventario=productos_filtrados,
        categorias=categorias,
        q=q,
        filtro_categoria=filtro_categoria,
        filtro_orden=filtro_orden,
        filtro_stock=filtro_stock,
        vista_tipo=vista_tipo,
        alertas_stock=alertas_stock,
        total_productos=len(inventario),
        productos_disponibles=len([p for p in inventario.values() if int(float(p.get("cantidad", 0) or 0)) > 0]),
        productos_agotados=len([p for p in inventario.values() if int(float(p.get("cantidad", 0) or 0)) <= 0]),
        productos_bajo_stock=len(alertas_stock),
        valor_total_inventario=valor_total
    )


def _registrar_kardex(producto_id: str, tipo: str, cantidad: int, stock_ant: int, stock_nvo: int, motivo: str, usuario: str = "SISTEMA"):
    try:
        from database import get_db_session, KardexMovimientoModel
        session = get_db_session()
        mov = KardexMovimientoModel(
            producto_id=str(producto_id),
            tipo=str(tipo),
            cantidad=int(cantidad),
            stock_anterior=int(stock_ant),
            stock_nuevo=int(stock_nvo),
            motivo=str(motivo),
            usuario=str(usuario),
            fecha=datetime.now().isoformat()
        )
        session.add(mov)
        session.commit()
        session.close()
    except Exception as e:
        print(f"Error registrando Kardex: {e}")


@inventario_bp.route("/inventario/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    """Formulario para registro de nuevos productos."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        precio_detal = float(request.form.get("precio_detal", 0) or 0)
        precio_mayor = float(request.form.get("precio_mayor", 0) or 0)
        costo_compra = float(request.form.get("costo_compra", 0) or 0)
        cantidad = int(request.form.get("cantidad", 0) or 0)
        stock_minimo = int(request.form.get("stock_minimo", 5) or 5)
        codigo = request.form.get("codigo", "").strip()

        if not nombre or not categoria:
            flash("El nombre y la categoría son requeridos", "danger")
            return render_template("producto_form.html")

        nuevo_id = str(max([int(k) for k in inventario.keys() if k.isdigit()] or [0]) + 1)
        inventario[nuevo_id] = {
            "nombre": nombre,
            "categoria": categoria,
            "precio": precio_detal,
            "precio_detal": precio_detal,
            "precio_usd": precio_detal,
            "precio_mayor_usd": precio_mayor,
            "costo_compra_usd": costo_compra,
            "cantidad": cantidad,
            "stock": cantidad,
            "stock_minimo": stock_minimo,
            "codigo": codigo,
            "fecha_creacion": datetime.now().isoformat(),
            "activo": True
        }

        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            _registrar_kardex(
                producto_id=nuevo_id,
                tipo="CREACION",
                cantidad=cantidad,
                stock_ant=0,
                stock_nvo=cantidad,
                motivo="Registro de nuevo producto",
                usuario="ADMINISTRADOR"
            )
            flash("Producto creado exitosamente", "success")
            return redirect(url_for("inventario.mostrar_inventario"))
        else:
            flash("Error al guardar el producto", "danger")

    return render_template("producto_form.html")


@inventario_bp.route("/inventario/<id>/editar", methods=["GET", "POST"])
@login_required
def editar_producto(id: str):
    """Edita un producto existente en el catálogo."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    if id not in inventario:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("inventario.mostrar_inventario"))

    if request.method == "POST":
        prod_prev = inventario[id]
        stock_ant = int(float(prod_prev.get("cantidad", 0) or 0))
        nueva_cant = int(request.form.get("cantidad", 0) or 0)
        precio_detal = float(request.form.get("precio_detal", 0) or 0)
        precio_mayor = float(request.form.get("precio_mayor", 0) or 0)
        costo_compra = float(request.form.get("costo_compra", 0) or 0)

        inventario[id].update({
            "nombre": request.form.get("nombre", "").strip(),
            "categoria": request.form.get("categoria", "").strip(),
            "precio": precio_detal,
            "precio_detal": precio_detal,
            "precio_usd": precio_detal,
            "precio_mayor_usd": precio_mayor,
            "costo_compra_usd": costo_compra,
            "cantidad": nueva_cant,
            "stock": nueva_cant,
            "stock_minimo": int(request.form.get("stock_minimo", 5) or 5),
            "codigo": request.form.get("codigo", "").strip(),
            "fecha_actualizacion": datetime.now().isoformat()
        })

        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            if stock_ant != nueva_cant:
                _registrar_kardex(
                    producto_id=id,
                    tipo="AJUSTE_EDICION",
                    cantidad=abs(nueva_cant - stock_ant),
                    stock_ant=stock_ant,
                    stock_nvo=nueva_cant,
                    motivo="Ajuste por edición de producto",
                    usuario="ADMINISTRADOR"
                )
            flash("Producto actualizado exitosamente", "success")
            return redirect(url_for("inventario.mostrar_inventario"))
        else:
            flash("Error al actualizar producto", "danger")

    return render_template("producto_form.html", producto=inventario[id], id=id)


@inventario_bp.route("/inventario/<id>/eliminar", methods=["POST"])
@login_required
def eliminar_producto(id: str):
    """Elimina un producto del catálogo."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    if id in inventario:
        del inventario[id]
        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            flash("Producto eliminado exitosamente", "success")
        else:
            flash("Error al eliminar producto", "danger")
    else:
        flash("Producto no encontrado", "danger")
    return redirect(url_for("inventario.mostrar_inventario"))


@inventario_bp.route("/inventario/dashboard")
@login_required
def dashboard_inventario():
    """Dashboard métrico y analítico de inventario."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    metricas = calcular_metricas_inventario(inventario)
    return render_template("inventario_dashboard.html", metricas=metricas, inventario=inventario)


@inventario_bp.route("/inventario/kardex/<id>")
@login_required
def ver_kardex(id: str):
    """Muestra el historial completo de movimientos Kardex para un producto."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    producto = inventario.get(id, {})
    movimientos = []
    try:
        from database import get_db_session, KardexMovimientoModel
        session = get_db_session()
        rows = session.query(KardexMovimientoModel).filter_by(producto_id=str(id)).order_by(KardexMovimientoModel.id.desc()).all()
        movimientos = [r.to_dict() for r in rows]
        session.close()
    except Exception:
        pass
    return render_template("inventario_kardex.html", producto=producto, id=id, movimientos=movimientos)


@inventario_bp.route("/inventario/etiquetas-pdf")
@login_required
def imprimir_etiquetas():
    """Genera plantilla de etiquetas de precio con códigos QR/Barras para imprimir."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    return render_template("inventario_etiquetas.html", inventario=inventario)


@inventario_bp.route("/inventario/generar-codigo-barras/<id>")
@login_required
def generar_codigo_barras(id: str):
    """Genera código QR/Barras para un producto."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    if id not in inventario:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("inventario.mostrar_inventario"))

    try:
        import qrcode
        from io import BytesIO
        import base64

        producto = inventario[id]
        qr_data = f"ID:{id}|Nombre:{producto.get('nombre')}|Precio:{producto.get('precio')}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_str = base64.b64encode(buf.getvalue()).decode()

        return render_template("codigo_barras.html", producto=producto, codigo_barras=img_str, qr_data=qr_data)
    except Exception as e:
        flash(f"Error generando código de barras: {e}", "danger")
        return redirect(url_for("inventario.mostrar_inventario"))


@inventario_bp.route("/inventario/prediccion-demandas")
@login_required
def prediccion_demandas():
    """Predicción básica de reabastecimiento basada en stock mínimo."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    predicciones = []
    for pid, p in inventario.items():
        if not isinstance(p, dict):
            continue
        cant = int(float(p.get("cantidad", 0) or 0))
        stock_min = int(float(p.get("stock_minimo", 5) or 5))
        if cant <= stock_min:
            predicciones.append({
                "id": pid,
                "nombre": p.get("nombre", ""),
                "categoria": p.get("categoria", ""),
                "stock_actual": cant,
                "recomendacion": "Reponer Stock Urgente" if cant <= 0 else "Nivel Bajo"
            })
    return render_template("prediccion_demandas.html", predicciones=predicciones)


@inventario_bp.route("/inventario/ajustar-stock", methods=["GET", "POST"])
@login_required
def ajustar_stock():
    """Ajuste rápido de inventario con registro automático en Kardex."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False) or {}
    if request.method == "POST":
        prod_id = request.form.get("producto_id", "")
        nueva_cant = int(request.form.get("cantidad", 0) or 0)
        motivo = request.form.get("motivo", "Ajuste manual de stock")
        if prod_id in inventario:
            stock_ant = int(float(inventario[prod_id].get("cantidad", 0) or 0))
            inventario[prod_id]["cantidad"] = nueva_cant
            inventario[prod_id]["stock"] = nueva_cant
            if guardar_datos(ARCHIVO_INVENTARIO, inventario):
                _registrar_kardex(
                    producto_id=prod_id,
                    tipo="ENTRADA" if nueva_cant > stock_ant else "SALIDA_AJUSTE",
                    cantidad=abs(nueva_cant - stock_ant),
                    stock_ant=stock_ant,
                    stock_nvo=nueva_cant,
                    motivo=motivo,
                    usuario="ADMINISTRADOR"
                )
                flash("Stock ajustado correctamente", "success")
                return redirect(url_for("inventario.mostrar_inventario"))
        flash("Error al ajustar stock", "danger")

    return render_template("ajustar_stock.html", inventario=inventario)



