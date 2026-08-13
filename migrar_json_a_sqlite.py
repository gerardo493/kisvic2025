# -*- coding: utf-8 -*-
"""
Script de Migración Automática de Kisvic: JSON -> SQLite (kisvic.db).
Transfiere facturas, clientes, inventario, cuentas por cobrar y empresa sin pérdida de datos.
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from database import (
    init_db, get_db_session,
    ClienteModel, ProductoModel, FacturaModel,
    CuentaPorCobrarModel, BitacoraModel, EmpresaModel
)
from almacenamiento import cargar_datos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def migrar_todo() -> dict:
    """Ejecuta la migración de todos los archivos JSON a la base de datos SQLite."""
    print("[migracion] Iniciando migracion de datos a SQLite (kisvic.db)...")
    init_db()
    session = get_db_session()

    stats = {
        "clientes": 0,
        "productos": 0,
        "facturas": 0,
        "cuentas": 0,
        "empresa": 0
    }

    try:
        # 1. Migrar Clientes
        clientes_data = cargar_datos("clientes.json", crear_vacio=False) or {}
        if isinstance(clientes_data, dict):
            for c_id, c in clientes_data.items():
                if not isinstance(c, dict):
                    continue
                cid = str(c.get("id") or c_id).strip()
                if not cid:
                    continue
                existente = session.query(ClienteModel).filter_by(id=cid).first()
                if not existente:
                    obj = ClienteModel(
                        id=cid,
                        nombre=str(c.get("nombre", "")),
                        rif=str(c.get("rif", "")),
                        telefono=str(c.get("telefono", "")),
                        direccion=str(c.get("direccion", "")),
                        email=str(c.get("email", "")),
                        estado=str(c.get("estado", "activo")),
                        fecha_registro=str(c.get("fecha_registro", ""))
                    )
                    session.add(obj)
                    stats["clientes"] += 1

        # 2. Migrar Inventario
        inventario_data = cargar_datos("inventario.json", crear_vacio=False) or {}
        if isinstance(inventario_data, dict):
            for p_id, p in inventario_data.items():
                if not isinstance(p, dict):
                    continue
                pid = str(p.get("id") or p_id).strip()
                if not pid:
                    continue
                existente = session.query(ProductoModel).filter_by(id=pid).first()
                if not existente:
                    historial_json = json.dumps(p.get("historial_ajustes", []), ensure_ascii=False)
                    obj = ProductoModel(
                        id=pid,
                        codigo=str(p.get("codigo", pid)),
                        nombre=str(p.get("nombre", "")),
                        descripcion=str(p.get("descripcion", "")),
                        precio_usd=float(p.get("precio_usd", 0.0) or 0.0),
                        precio_bs=float(p.get("precio_bs", 0.0) or 0.0),
                        stock=int(p.get("stock", 0) or 0),
                        stock_minimo=int(p.get("stock_minimo", 5) or 5),
                        categoria=str(p.get("categoria", "General")),
                        unidad_medida=str(p.get("unidad_medida", "UNID")),
                        historial_ajustes_json=historial_json
                    )
                    session.add(obj)
                    stats["productos"] += 1

        # 3. Migrar Facturas (Maestro + Archivos Individuales)
        raw_facturas = cargar_datos("facturas_json/facturas.json", crear_vacio=False) or {}
        if not isinstance(raw_facturas, dict):
            raw_facturas = {}

        facturas_dir = os.path.join(BASE_DIR, "facturas_json")
        if os.path.exists(facturas_dir):
            for fname in os.listdir(facturas_dir):
                if fname.endswith(".json") and fname != "facturas.json":
                    f_key = fname[len("factura_"):-len(".json")] if fname.startswith("factura_") else fname[:-len(".json")]
                    if f_key not in raw_facturas:
                        fdata = cargar_datos(os.path.join("facturas_json", fname), crear_vacio=False)
                        if fdata and isinstance(fdata, dict):
                            raw_facturas[f_key] = fdata

        facturas_unificadas = {}
        vistos = set()
        for k, f in raw_facturas.items():
            if not isinstance(f, dict):
                continue
            num = str(f.get("numero", "")).strip()
            fid = str(f.get("id", "")).strip()
            sec = str(f.get("numero_secuencial", "")).strip()
            ukey = num or fid or sec or str(k).strip()

            if ukey in vistos:
                continue
            vistos.add(ukey)
            pkey = fid or str(k).strip() or num
            facturas_unificadas[pkey] = f

        for fid, f in facturas_unificadas.items():
            existente = session.query(FacturaModel).filter_by(id=fid).first()
            if not existente:
                obj = FacturaModel(
                    id=fid,
                    numero=str(f.get("numero", fid)),
                    numero_secuencial=str(f.get("numero_secuencial", "")),
                    cliente_id=str(f.get("cliente_id", "")),
                    fecha=str(f.get("fecha", "")),
                    hora=str(f.get("hora", "")),
                    condicion_pago=str(f.get("condicion_pago", "contado")),
                    dias_credito=str(f.get("dias_credito", "30")),
                    tasa_bcv=float(f.get("tasa_bcv", 36.0) or 36.0),
                    subtotal_usd=float(f.get("subtotal_usd", 0.0) or 0.0),
                    descuento_total=float(f.get("descuento_total", 0.0) or 0.0),
                    iva_porcentaje=float(f.get("iva_porcentaje", 0.0) or 0.0),
                    iva_total=float(f.get("iva_total", 0.0) or 0.0),
                    total_usd=float(f.get("total_usd", 0.0) or 0.0),
                    total_bs=float(f.get("total_bs", 0.0) or 0.0),
                    total_abonado=float(f.get("total_abonado", 0.0) or 0.0),
                    saldo_pendiente=float(f.get("saldo_pendiente", 0.0) or 0.0),
                    estado=str(f.get("estado", "pendiente")),
                    firma_fiscal=str(f.get("firma_fiscal", "")),
                    creado_por=str(f.get("creado_por", "SISTEMA")),
                    fecha_creacion=str(f.get("fecha_creacion", "")),
                    productos_json=json.dumps(f.get("productos", []), ensure_ascii=False),
                    cantidades_json=json.dumps(f.get("cantidades", []), ensure_ascii=False),
                    precios_json=json.dumps(f.get("precios", []), ensure_ascii=False),
                    pagos_json=json.dumps(f.get("pagos", []), ensure_ascii=False)
                )
                session.add(obj)
                stats["facturas"] += 1

        # 4. Migrar Cuentas Por Cobrar
        cuentas_data = cargar_datos("cuentas_por_cobrar.json", crear_vacio=False) or {}
        if isinstance(cuentas_data, dict):
            for c_key, c in cuentas_data.items():
                if not isinstance(c, dict):
                    continue
                num_fac = str(c.get("numero_factura") or c_key).strip()
                existente = session.query(CuentaPorCobrarModel).filter_by(numero_factura=num_fac).first()
                if not existente and num_fac:
                    obj = CuentaPorCobrarModel(
                        numero_factura=num_fac,
                        cliente_id=str(c.get("cliente_id", "")),
                        monto_total=float(c.get("monto_total", 0.0) or 0.0),
                        monto_pendiente=float(c.get("monto_pendiente", 0.0) or 0.0),
                        fecha_emision=str(c.get("fecha_emision", "")),
                        estado=str(c.get("estado", "pendiente"))
                    )
                    session.add(obj)
                    stats["cuentas"] += 1

        # 5. Migrar Datos de la Empresa
        empresa_data = cargar_datos("empresa.json", crear_vacio=False)
        if isinstance(empresa_data, dict) and empresa_data:
            emp = session.query(EmpresaModel).filter_by(id=1).first()
            if not emp:
                emp = EmpresaModel(
                    id=1,
                    nombre=str(empresa_data.get("nombre", "")),
                    rif=str(empresa_data.get("rif", "")),
                    telefono=str(empresa_data.get("telefono", "")),
                    direccion=str(empresa_data.get("direccion", ""))
                )
                session.add(emp)
                stats["empresa"] += 1

        session.commit()
        print("[migracion] OK: Migracion a SQLite completada exitosamente")
        print(f"   * Clientes migrados: {stats['clientes']}")
        print(f"   * Productos migrados: {stats['productos']}")
        print(f"   * Facturas migradas: {stats['facturas']}")
        print(f"   * Cuentas por cobrar migradas: {stats['cuentas']}")
        print(f"   * Datos de Empresa migrados: {stats['empresa']}")
    except Exception as e:
        session.rollback()
        print(f"[migracion] ERROR durante la migracion: {e}")
    finally:
        session.close()

    return stats


if __name__ == "__main__":
    migrar_todo()
