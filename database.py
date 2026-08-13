# -*- coding: utf-8 -*-
"""
Módulo de Base de Datos Relacional Kisvic (SQLite + SQLAlchemy ORM).
Garantiza transacciones ACID, concurrencia segura y consultas indexadas.
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import (
    create_engine, event, Column, String, Float, Integer, Text, DateTime, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kisvic.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

# Activar modo WAL (Write-Ahead Logging) en SQLite para alto rendimiento y concurrencia
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ClienteModel(Base):
    __tablename__ = "clientes"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, index=True)
    rif = Column(String, index=True)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    email = Column(String, nullable=True)
    estado = Column(String, default="activo")
    fecha_registro = Column(String, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre or "",
            "rif": self.rif or "",
            "telefono": self.telefono or "",
            "direccion": self.direccion or "",
            "email": self.email or "",
            "estado": self.estado or "activo",
            "fecha_registro": self.fecha_registro or ""
        }


class ProductoModel(Base):
    __tablename__ = "inventario"

    id = Column(String, primary_key=True, index=True)
    codigo = Column(String, index=True, nullable=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text, nullable=True)
    precio_usd = Column(Float, default=0.0)
    precio_mayor_usd = Column(Float, default=0.0)
    costo_compra_usd = Column(Float, default=0.0)
    precio_bs = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=5)
    categoria = Column(String, nullable=True)
    unidad_medida = Column(String, default="UNID")
    historial_ajustes_json = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        historial = []
        if self.historial_ajustes_json:
            try:
                historial = json.loads(self.historial_ajustes_json)
            except Exception:
                historial = []
        p_usd = float(self.precio_usd or 0.0)
        p_mayor = float(self.precio_mayor_usd or 0.0)
        costo = float(self.costo_compra_usd or 0.0)
        stk = int(self.stock or 0)
        margen = round(((p_usd - costo) / p_usd * 100), 2) if (p_usd > 0 and costo > 0) else 0.0

        return {
            "id": self.id,
            "codigo": self.codigo or self.id,
            "nombre": self.nombre or "",
            "descripcion": self.descripcion or "",
            "precio_usd": p_usd,
            "precio": p_usd,
            "precio_detal": p_usd,
            "precio_mayor_usd": p_mayor,
            "costo_compra_usd": costo,
            "margen_ganancia_porcentaje": margen,
            "precio_bs": float(self.precio_bs or 0.0),
            "stock": stk,
            "cantidad": stk,
            "stock_minimo": int(self.stock_minimo or 5),
            "categoria": self.categoria or "General",
            "unidad_medida": self.unidad_medida or "UNID",
            "historial_ajustes": historial
        }


class KardexMovimientoModel(Base):
    __tablename__ = "kardex_movimientos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(String, index=True)
    tipo = Column(String, index=True)
    cantidad = Column(Integer, default=0)
    stock_anterior = Column(Integer, default=0)
    stock_nuevo = Column(Integer, default=0)
    motivo = Column(String, nullable=True)
    usuario = Column(String, default="SISTEMA")
    fecha = Column(String, default=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "producto_id": self.producto_id or "",
            "tipo": self.tipo or "AJUSTE",
            "cantidad": int(self.cantidad or 0),
            "stock_anterior": int(self.stock_anterior or 0),
            "stock_nuevo": int(self.stock_nuevo or 0),
            "motivo": self.motivo or "",
            "usuario": self.usuario or "SISTEMA",
            "fecha": self.fecha or ""
        }


class FacturaModel(Base):
    __tablename__ = "facturas"

    id = Column(String, primary_key=True, index=True)
    numero = Column(String, index=True, nullable=True)
    numero_secuencial = Column(String, index=True, nullable=True)
    cliente_id = Column(String, index=True, nullable=True)
    fecha = Column(String, index=True, nullable=True)
    hora = Column(String, nullable=True)
    condicion_pago = Column(String, default="contado")
    dias_credito = Column(String, default="30")
    tasa_bcv = Column(Float, default=36.0)
    subtotal_usd = Column(Float, default=0.0)
    descuento_total = Column(Float, default=0.0)
    iva_porcentaje = Column(Float, default=0.0)
    iva_total = Column(Float, default=0.0)
    total_usd = Column(Float, default=0.0)
    total_bs = Column(Float, default=0.0)
    total_abonado = Column(Float, default=0.0)
    saldo_pendiente = Column(Float, default=0.0)
    estado = Column(String, index=True, default="pendiente")
    firma_fiscal = Column(String, nullable=True)
    creado_por = Column(String, nullable=True)
    fecha_creacion = Column(String, nullable=True)

    productos_json = Column(Text, nullable=True)
    cantidades_json = Column(Text, nullable=True)
    precios_json = Column(Text, nullable=True)
    pagos_json = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        prods = json.loads(self.productos_json) if self.productos_json else []
        cants = json.loads(self.cantidades_json) if self.cantidades_json else []
        precs = json.loads(self.precios_json) if self.precios_json else []
        pagos = json.loads(self.pagos_json) if self.pagos_json else []

        return {
            "id": self.id,
            "numero": self.numero or self.id,
            "numero_secuencial": self.numero_secuencial or "",
            "cliente_id": self.cliente_id or "",
            "fecha": self.fecha or "",
            "hora": self.hora or "",
            "condicion_pago": self.condicion_pago or "contado",
            "dias_credito": self.dias_credito or "30",
            "tasa_bcv": float(self.tasa_bcv or 1.0),
            "subtotal_usd": float(self.subtotal_usd or 0.0),
            "descuento_total": float(self.descuento_total or 0.0),
            "iva_porcentaje": float(self.iva_porcentaje or 0.0),
            "iva_total": float(self.iva_total or 0.0),
            "total_usd": float(self.total_usd or 0.0),
            "total_bs": float(self.total_bs or 0.0),
            "total_abonado": float(self.total_abonado or 0.0),
            "saldo_pendiente": float(self.saldo_pendiente or 0.0),
            "estado": self.estado or "pendiente",
            "firma_fiscal": self.firma_fiscal or "",
            "creado_por": self.creado_por or "",
            "fecha_creacion": self.fecha_creacion or "",
            "productos": prods,
            "cantidades": cants,
            "precios": precs,
            "pagos": pagos
        }


class CuentaPorCobrarModel(Base):
    __tablename__ = "cuentas_por_cobrar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_factura = Column(String, index=True)
    cliente_id = Column(String, index=True)
    monto_total = Column(Float, default=0.0)
    monto_pendiente = Column(Float, default=0.0)
    fecha_emision = Column(String, nullable=True)
    estado = Column(String, default="pendiente")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "numero_factura": self.numero_factura or "",
            "cliente_id": self.cliente_id or "",
            "monto_total": float(self.monto_total or 0.0),
            "monto_pendiente": float(self.monto_pendiente or 0.0),
            "fecha_emision": self.fecha_emision or "",
            "estado": self.estado or "pendiente"
        }


class BitacoraModel(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String, index=True)
    accion = Column(String)
    detalle = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "usuario": self.usuario or "SISTEMA",
            "accion": self.accion or "",
            "detalle": self.detalle or "",
            "timestamp": self.timestamp or datetime.now().isoformat()
        }


class EmpresaModel(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True, default=1)
    nombre = Column(String)
    rif = Column(String)
    telefono = Column(String)
    direccion = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre or "Nombre de la Empresa",
            "rif": self.rif or "J-000000000",
            "telefono": self.telefono or "0000-0000000",
            "direccion": self.direccion or "Dirección de la Empresa"
        }


def init_db():
    """Inicializa y crea todas las tablas en kisvic.db si no existen."""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """Retorna una sesión activa de SQLAlchemy."""
    return SessionLocal()
