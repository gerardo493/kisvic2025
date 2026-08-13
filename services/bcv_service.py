# -*- coding: utf-8 -*-
"""
Módulo de servicio para la gestión y consulta de la tasa BCV (USD/VES).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
import requests
import urllib3
from bs4 import BeautifulSoup
from almacenamiento import cargar_datos, guardar_datos

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ULTIMA_TASA_BCV_FILE = "ultima_tasa_bcv.json"
ARCHIVO_FACTURAS = "facturas_json/facturas.json"
ARCHIVO_COTIZACIONES = "cotizaciones_json/cotizaciones.json"


def cargar_ultima_tasa_bcv() -> float | None:
    """Carga la última tasa BCV guardada desde el almacenamiento local."""
    try:
        data = cargar_datos(ULTIMA_TASA_BCV_FILE, crear_vacio=False) or {}
        tasa = float(data.get("tasa", 0))
        return tasa if tasa > 10 else None
    except Exception as e:
        print(f"Error cargando tasa BCV local: {e}")
        return None


def guardar_ultima_tasa_bcv(tasa: float) -> bool:
    """Guarda la tasa BCV especificada en el almacenamiento local."""
    try:
        data = {
            "tasa": float(tasa),
            "fecha": datetime.now().isoformat(),
            "ultima_actualizacion": datetime.now().isoformat(),
        }
        guardar_datos(ULTIMA_TASA_BCV_FILE, data)
        print(f"Tasa BCV guardada exitosamente: {tasa}")
        return True
    except Exception as e:
        print(f"Error guardando última tasa BCV: {e}")
        return False


def obtener_ultima_tasa_del_sistema() -> float | None:
    """Busca la tasa más reciente registrada en facturas o cotizaciones."""
    tasas_encontradas: list[float] = []
    fuentes = [ARCHIVO_FACTURAS, ARCHIVO_COTIZACIONES]

    for fuente in fuentes:
        try:
            registros = cargar_datos(fuente, crear_vacio=False) or {}
            for item in registros.values():
                if isinstance(item, dict) and item.get("tasa_bcv"):
                    try:
                        val = float(item["tasa_bcv"])
                        if val > 10:
                            tasas_encontradas.append(val)
                    except (ValueError, TypeError):
                        continue
        except Exception:
            continue

    return max(tasas_encontradas) if tasas_encontradas else None



def obtener_tasa_bcv_dia() -> float | None:
    """Scrapea la tasa oficial USD/VES del portal web del BCV."""
    url = "https://www.bcv.org.ve/glosario/cambio-oficial"
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, timeout=20, verify=False)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        tasa = _extraer_tasa_html(soup, resp.text)

        if tasa and tasa > 10:
            guardar_ultima_tasa_bcv(tasa)
            return tasa
    except Exception as e:
        print(f"Error extrayendo tasa BCV desde la web: {e}")

    return cargar_ultima_tasa_bcv()


def _extraer_tasa_html(soup: BeautifulSoup, html_raw: str) -> float | None:
    """Helper privado para parsear el HTML del BCV buscando la tasa."""
    for element_id in ["dolar", "usd"]:
        elem = soup.find("div", id=element_id)
        if elem and elem.find("strong"):
            val = _parse_monto(elem.find("strong").text)
            if val and val > 10:
                return val

    for strong in soup.find_all("strong"):
        val = _parse_monto(strong.text)
        if val and 10 < val < 1000:
            return val

    matches = re.findall(r"(\d{2,}[.,]\d{2,})", html_raw)
    for match in matches:
        val = _parse_monto(match)
        if val and 10 < val < 1000:
            return val

    return None


def _parse_monto(texto: str) -> float | None:
    """Convierte texto numérico con formato español/inglés a float."""
    try:
        clean = texto.strip().replace(".", "").replace(",", ".")
        return float(clean)
    except (ValueError, TypeError):
        return None


def obtener_tasa_bcv() -> float | None:
    """Obtiene la tasa BCV (de la caché local o del sistema como fallback)."""
    tasa = cargar_ultima_tasa_bcv()
    if tasa:
        return tasa
    return obtener_ultima_tasa_del_sistema()


def actualizar_tasa_bcv_automaticamente() -> None:
    """Comprueba la antigüedad de la tasa y la actualiza si han transcurrido > 24 horas."""
    try:
        data = cargar_datos(ULTIMA_TASA_BCV_FILE, crear_vacio=False) or {}
        ultima_fecha_str = data.get("fecha", "")

        if ultima_fecha_str:
            ultima_fecha = datetime.fromisoformat(ultima_fecha_str)
            if (datetime.now() - ultima_fecha).total_seconds() > 86400:
                obtener_tasa_bcv_dia()
        else:
            obtener_tasa_bcv_dia()
    except Exception as e:
        print(f"Error en actualización automática BCV: {e}")


def inicializar_archivos_por_defecto() -> None:
    """Inicializa archivos de almacenamiento basales si no existen."""
    archivos = [ULTIMA_TASA_BCV_FILE, ARCHIVO_FACTURAS, ARCHIVO_COTIZACIONES]
    for fn in archivos:
        if not os.path.exists(os.path.join(BASE_DIR, fn)):
            cargar_datos(fn, crear_vacio=True)


