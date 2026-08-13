# -*- coding: utf-8 -*-
"""
Módulo de constantes y enums del sistema KISVIC.
Establece la fuente única de verdad para estados de factura, tolerancias y configuraciones por defecto.
"""

from __future__ import annotations
from enum import Enum


class EstadoFactura(str, Enum):
    PENDIENTE = "pendiente"
    ABONADA = "abonada"
    PAGADA = "pagada"

    @classmethod
    def from_string(cls, val: str | None) -> EstadoFactura:
        """Normaliza cualquier varianza de texto a un estado canónico de factura."""
        if not val:
            return cls.PENDIENTE
        v = str(val).lower().strip()
        if v in ("cobrada", "cobradas", "pagada", "pagadas", "cobrado"):
            return cls.PAGADA
        elif v in ("abonada", "abonadas", "abono"):
            return cls.ABONADA
        return cls.PENDIENTE

    @property
    def label(self) -> str:
        """Retorna la etiqueta legible para la interfaz de usuario."""
        if self == EstadoFactura.PAGADA:
            return "Cobrada"
        elif self == EstadoFactura.ABONADA:
            return "Abonada"
        return "Por Cobrar"

    @property
    def key_filtro(self) -> str:
        """Clave usada para filtrados en URLs y vistas."""
        if self == EstadoFactura.PAGADA:
            return "cobrada"
        elif self == EstadoFactura.ABONADA:
            return "abonada"
        return "por_cobrar"

    @property
    def badge_class(self) -> str:
        """Retorna las clases CSS de Bootstrap garantizando contraste WCAG AA."""
        if self == EstadoFactura.PAGADA:
            return "bg-success text-white"
        elif self == EstadoFactura.ABONADA:
            return "bg-info text-dark"
        return "bg-warning text-dark"


TOLERANCIA_SALDO: float = 0.01
DIAS_VENCIMIENTO_DEFAULT: int = 30
TASA_BCV_FALLBACK: float = 36.00
