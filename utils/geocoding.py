# -*- coding: utf-8 -*-
"""
Módulo de geocodificación comercial con Nominatim / OpenStreetMap.
Cumple con la política de uso de OSM (User-Agent válido y tiempo de retardo).
"""

from __future__ import annotations
import time
import requests

HEADERS = {"User-Agent": "KisvicCuentasPorCobrar/1.0 (contacto@kisvic.com)"}

ESTADOS_VENEZUELA = [
    "Distrito Capital", "Miranda", "Aragua", "Carabobo", "Zulia",
    "Lara", "Anzoátegui", "Monagas", "Bolívar", "Sucre", "Falcón",
    "Táchira", "Mérida", "Trujillo", "Nueva Esparta", "Yaracuy",
    "Portuguesa", "Barinas", "Guárico", "Apure", "Cojedes",
    "Delta Amacuro", "Amazonas", "La Guaira"
]

MUNICIPIOS_POR_ESTADO = {
    "Distrito Capital": ["Libertador"],
    "Miranda": ["Chacao", "Baruta", "Sucre", "El Hatillo", "Guarenas", "Guatire", "Los Salias", "Carrizal", "Guaicaipuro", "Urdaneta", "Lander", "Independencia", "Paz Castillo", "Brión"],
    "Aragua": ["Girardot", "Santiago Mariño", "José Félix Ribas", "José Ángel Lamas", "Sucre", "Zamora", "MBI"],
    "Carabobo": ["Valencia", "Naguanagua", "San Diego", "Guacara", "Puerto Cabello", "Los Guayos", "San Joaquín"],
    "Zulia": ["Maracaibo", "San Francisco", "Cabimas", "Lagunillas", "Baralt", "Rosario de Perijá", "Machiques"],
    "Lara": ["Iribarren", "Palavecino", "Torres", "Jiménez", "Morán", "Crespo"],
    "Anzoátegui": ["Simón Bolívar", "Juan Antonio Sotillo", "Diego Bautista Urbaneja", "Anaco", "Simón Rodríguez", "Freites"],
    "Monagas": ["Maturín", "Ezequiel Zamora", "Cedeño", "Piar", "Caripe", "Bolívar"],
    "Bolívar": ["Caroní", "Angostura del Orinoco", "Piar", "Roscio", "Sifontes"],
    "Sucre": ["Sucre", "Bermúdez", "Montes", "Ribero", "Valdez"],
    "Falcón": ["Miranda", "Carirubana", "Silva", "Federación"],
    "Táchira": ["San Cristóbal", "Cárdenas", "Torbes", "Jáuregui", "Junín"],
    "Mérida": ["Libertador", "Alberto Adriani", "Campo Elías", "Sucre"],
    "Trujillo": ["Valera", "Trujillo", "Bocoñó", "Sucre"],
    "Nueva Esparta": ["Mariño", "Maneiro", "Arismendi", "García", "Díaz"],
    "Yaracuy": ["San Felipe", "Peña", "Bruzual", "Nirgua"],
    "Portuguesa": ["Páez", "Araure", "Guanare", "Turén"],
    "Barinas": ["Barinas", "Bolívar", "Pedraza", "Sucre"],
    "Guárico": ["Juan Germán Roscio", "Leonardo Infante", "Francisco de Miranda"],
    "Apure": ["San Fernando", "Biruaca", "Achaguas"],
    "Cojedes": ["Ezequiel Zamora", "Tinaquillo"],
    "Delta Amacuro": ["Tucupita"],
    "Amazonas": ["Atures"],
    "La Guaira": ["Vargas"]
}


def detectar_estado_municipio(direccion: str) -> tuple[str, str]:
    """Extrae el estado y municipio inferidos a partir de una cadena de dirección."""
    dir_lower = (direccion or "").lower()
    estado_encontrado = ""
    municipio_encontrado = ""

    for est in ESTADOS_VENEZUELA:
        if est.lower() in dir_lower:
            estado_encontrado = est
            break

    if not estado_encontrado:
        if "caracas" in dir_lower:
            estado_encontrado = "Distrito Capital"
        elif "maracay" in dir_lower:
            estado_encontrado = "Aragua"
        elif "valencia" in dir_lower or "naguanagua" in dir_lower:
            estado_encontrado = "Carabobo"
        elif "maracaibo" in dir_lower:
            estado_encontrado = "Zulia"
        elif "barquisimeto" in dir_lower:
            estado_encontrado = "Lara"
        elif "puerto la cruz" in dir_lower or "barcelona" in dir_lower or "lecheria" in dir_lower:
            estado_encontrado = "Anzoátegui"
        elif "maturin" in dir_lower or "punta de mata" in dir_lower:
            estado_encontrado = "Monagas"
        elif "san felix" in dir_lower or "puerto ordaz" in dir_lower or "ciudad bolivar" in dir_lower or "guayana" in dir_lower:
            estado_encontrado = "Bolívar"
        elif "cumana" in dir_lower:
            estado_encontrado = "Sucre"
        elif "porlamar" in dir_lower or "margarita" in dir_lower:
            estado_encontrado = "Nueva Esparta"
        elif "san cristobal" in dir_lower:
            estado_encontrado = "Táchira"
        elif "merida" in dir_lower:
            estado_encontrado = "Mérida"

    if estado_encontrado and estado_encontrado in MUNICIPIOS_POR_ESTADO:
        for mun in MUNICIPIOS_POR_ESTADO[estado_encontrado]:
            if mun.lower() in dir_lower:
                municipio_encontrado = mun
                break

    return estado_encontrado, municipio_encontrado


def geocodificar_direccion(direccion: str, municipio: str = "", estado: str = "") -> tuple[float | None, float | None]:
    """
    Geocodifica una dirección usando la API gratuita de Nominatim.
    Retorna (latitud, longitud) o (None, None) si no encuentra ubicación válida.
    """
    partes = []
    if direccion:
        partes.append(direccion.strip())
    if municipio:
        partes.append(municipio.strip())
    if estado:
        partes.append(estado.strip())
    partes.append("Venezuela")

    query = ", ".join([p for p in partes if p])
    if not query or query == "Venezuela":
        return None, None

    url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&limit=1&countrycodes=ve"

    try:
        res = requests.get(url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            datos = res.json()
            if isinstance(datos, list) and len(datos) > 0:
                lat = float(datos[0]["lat"])
                lon = float(datos[0]["lon"])
                return lat, lon

        if (municipio or estado):
            fb_parts = [p for p in [municipio, estado, "Venezuela"] if p]
            fb_query = ", ".join(fb_parts)
            fb_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(fb_query)}&format=json&limit=1&countrycodes=ve"
            time.sleep(1)
            res_fb = requests.get(fb_url, headers=HEADERS, timeout=4)
            if res_fb.status_code == 200:
                datos_fb = res_fb.json()
                if isinstance(datos_fb, list) and len(datos_fb) > 0:
                    return float(datos_fb[0]["lat"]), float(datos_fb[0]["lon"])
    except Exception as e:
        print(f"[geocodificación] Excepción en Nominatim para '{query}': {e}")

    return None, None
