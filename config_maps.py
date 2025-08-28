# Configuración para Google Maps API
import os

# Configuración de Google Maps API
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyDwc6TnKyHP0Q6O6tNo4_RfK24CuKvM524')

# Configuración de límites de uso
MAPS_QUOTA_LIMIT = 1000  # Límite diario de solicitudes
MAPS_RATE_LIMIT = 10     # Solicitudes por segundo

# Configuración de geocoding
GEOCODING_TIMEOUT = 5    # Timeout en segundos para geocoding
MAX_GEOCODING_RETRIES = 3

# Configuración de clustering
CLUSTER_GRID_SIZE = 50
CLUSTER_MAX_ZOOM = 15

# Configuración de heatmap
HEATMAP_RADIUS = 20
HEATMAP_OPACITY = 0.6

# Configuración de rutas
ROUTE_ALTERNATIVES = True
ROUTE_OPTIMIZE_WAYPOINTS = True

# Configuración de marcadores
DEFAULT_MARKER_SIZE = 32
CUSTOM_MARKER_COLORS = {
    'cliente': 'red',
    'ubicacion_actual': 'blue',
    'destino': 'green',
    'punto_interes': 'yellow'
}

# Configuración de ventanas de información
INFO_WINDOW_MAX_WIDTH = 300
INFO_WINDOW_MAX_HEIGHT = 400

# Configuración de zoom
DEFAULT_ZOOM = 12
MIN_ZOOM = 8
MAX_ZOOM = 20

# Configuración de centro por defecto (Venezuela)
DEFAULT_CENTER = {
    'lat': 10.5,
    'lng': -66.9
}

# Configuración de tipos de mapa disponibles
MAP_TYPES = {
    'roadmap': 'Mapa',
    'satellite': 'Satélite', 
    'hybrid': 'Híbrido',
    'terrain': 'Terreno'
}

# Configuración de librerías de Google Maps
GOOGLE_MAPS_LIBRARIES = [
    'geometry',
    'places', 
    'visualization'
]

def get_maps_config():
    """Retorna la configuración completa de Google Maps"""
    return {
        'api_key': GOOGLE_MAPS_API_KEY,
        'libraries': GOOGLE_MAPS_LIBRARIES,
        'default_center': DEFAULT_CENTER,
        'default_zoom': DEFAULT_ZOOM,
        'map_types': MAP_TYPES,
        'clustering': {
            'grid_size': CLUSTER_GRID_SIZE,
            'max_zoom': CLUSTER_MAX_ZOOM
        },
        'heatmap': {
            'radius': HEATMAP_RADIUS,
            'opacity': HEATMAP_OPACITY
        },
        'geocoding': {
            'timeout': GEOCODING_TIMEOUT,
            'max_retries': MAX_GEOCODING_RETRIES
        }
    }

def is_api_key_valid():
    """Verifica si la API key es válida (no es la key por defecto)"""
    return GOOGLE_MAPS_API_KEY != 'AIzaSyDwc6TnKyHP0Q6O6tNo4_RfK24CuKvM524'

def get_api_key_warning():
    """Retorna un mensaje de advertencia si se está usando la key por defecto"""
    # No mostrar advertencia - usar la key por defecto sin problemas
    return None
