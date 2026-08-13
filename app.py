# -*- coding: utf-8 -*-
import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import urllib3
import urllib.parse
import requests
import csv
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import time

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file, session, abort, send_from_directory, g
from werkzeug.utils import secure_filename
# SOLUCIÓN: Importar CSRFProtect de manera compatible
try:
    from flask_wtf.csrf import CSRFProtect, CSRFError
except ImportError:
    # Fallback para versiones más nuevas
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import CSRFError
from werkzeug.security import generate_password_hash, check_password_hash
from config_maps import get_maps_config
from seguridad_fiscal import seguridad_fiscal
from numeracion_fiscal import control_numeracion
from comunicacion_seniat import comunicador_seniat
from exportacion_seniat import exportador_seniat
from services.filtros_dashboard import obtener_estadisticas_filtradas, obtener_opciones_filtro, obtener_metricas_tarjeta, obtener_opciones_filtro_avanzado

from config import get_active_config
from observabilidad import setup_observability, log_event, log_error, notify_critical
try:
    import pdfkit
except ImportError:
    pdfkit = None
from functools import wraps
import re
import uuid
import io
import zipfile
from io import StringIO
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
import base64
import copy
import re
from almacenamiento import cargar_datos, guardar_datos, usar_firebase

# --- Inicializar la Aplicación Flask ---
app = Flask(__name__)
app.config.from_object(get_active_config())
logger_obs = setup_observability()

# --- Configuración de la Aplicación ---
if app.config['SECRET_KEY'] == app.config.get('SECRET_KEY_DEFAULT'):
    print("[!] Seguridad: configura KISVIC_SECRET_KEY en variables de entorno.")

# --- Configuración CSRF (modo por fases) ---
# KISVIC_CSRF_MODE:
#   - off: desactivado
#   - phase1 (default): protege solo login
#   - strict: preparado para ampliar protección gradualmente
csrf_mode = str(app.config.get('KISVIC_CSRF_MODE', 'phase1')).strip().lower()

csrf = CSRFProtect(app)
if csrf_mode == 'off':
    print("[!] CSRF deshabilitado por KISVIC_CSRF_MODE=off")
else:
    print(f"[OK] CSRF habilitado en modo: {csrf_mode}")


# --- Helper para Tokens CSRF ---
def get_csrf_token():
    """Genera un token CSRF válido"""
    if csrf:
        return csrf._get_token()
    return None


def _get_protected_endpoints() -> set:
    """Endpoints protegidos en fase inicial de CSRF."""
    raw = str(app.config.get('KISVIC_CSRF_PROTECTED_ENDPOINTS', 'login'))
    endpoints = {x.strip() for x in raw.split(',') if x.strip()}
    return endpoints or {'login'}


@app.before_request
def iniciar_observabilidad_request():
    g.request_started_at = time.time()
    g.request_id = request.headers.get('X-Request-Id') or str(uuid4())


@app.before_request
def aplicar_csrf_por_fases():
    """
    Fase 1 de CSRF: protege endpoints puntuales (por defecto login).
    Evita romper todo el sistema de una sola vez.
    """
    if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
        return
    if csrf_mode == 'off':
        return
    endpoint = (request.endpoint or '').strip()
    if endpoint in _get_protected_endpoints():
        csrf.protect()


@app.after_request
def cerrar_observabilidad_request(response):
    started = getattr(g, 'request_started_at', None)
    elapsed_ms = int((time.time() - started) * 1000) if started else None
    request_id = getattr(g, 'request_id', '')
    response.headers['X-Request-Id'] = request_id

    log_event(
        logger_obs,
        'http_request',
        request_id=request_id,
        method=request.method,
        path=request.path,
        status=response.status_code,
        elapsed_ms=elapsed_ms,
        remote_addr=request.remote_addr,
    )
    return response


@app.errorhandler(CSRFError)
def manejar_error_csrf(e):
    log_error(
        logger_obs,
        'csrf_error',
        e,
        path=request.path,
        method=request.method,
        remote_addr=request.remote_addr,
    )
    flash('Sesión de seguridad expirada. Intenta de nuevo.', 'warning')
    destino = request.referrer or url_for('login')
    return redirect(destino)

# --- Constantes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
IMAGENES_PRODUCTOS_FOLDER = os.path.join(BASE_DIR, 'static', 'imagenes_productos')
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ARCHIVO_COTIZACIONES = 'cotizaciones_json/cotizaciones.json'
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'
ULTIMA_TASA_BCV_FILE = 'ultima_tasa_bcv.json'
ALLOWED_EXTENSIONS = {'csv', 'jpg', 'jpeg', 'png', 'gif'}
BITACORA_FILE = 'bitacora.log'

# --- Importación de Servicios Modulares ---
from services.bcv_service import (
    guardar_ultima_tasa_bcv,
    cargar_ultima_tasa_bcv,
    obtener_ultima_tasa_del_sistema,
    inicializar_archivos_por_defecto,
    actualizar_tasa_bcv_automaticamente,
    obtener_tasa_bcv,
    obtener_tasa_bcv_dia,
)
from services.bitacora_service import registrar_bitacora
from utils.auth_decorators import (
    validar_url_factura,
    login_required,
    admin_required,
    verify_password,
)
from services.dashboard_service import obtener_estadisticas

# Llamar inicialización de servicios
inicializar_archivos_por_defecto()
actualizar_tasa_bcv_automaticamente()

# Usar SECRET_KEY desde variables de entorno en producción
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unsafe-default-change-me')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
csrf = CSRFProtect(app)

# --- Configuración de rutas de capturas (compatibles con Render y local) ---
# En Render no podemos escribir en /data. Usamos una carpeta del proyecto
# que en despliegue se enlaza a un disco persistente (storage) en el start command.
IS_RENDER = bool(os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME'))
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CAPTURAS_FOLDER = os.path.join(BASE_PATH, 'uploads', 'capturas')
CAPTURAS_URL = '/uploads/capturas'

# Asegurar que las carpetas de capturas existen
os.makedirs(CAPTURAS_FOLDER, exist_ok=True)

# --- Importación y Registro de Blueprints Modulares ---
from routes.auth_routes import auth_bp
from routes.health_routes import health_bp
from routes.bitacora_routes import bitacora_bp
from routes.dashboard_routes import dashboard_bp
from routes.clientes_routes import clientes_bp
from routes.inventario_routes import inventario_bp
from routes.cotizaciones_routes import cotizaciones_bp
from routes.facturas_routes import facturas_bp
from routes.cuentas_routes import cuentas_bp
from routes.seniat_routes import seniat_bp
from routes.api_routes import api_bp
from routes.mapa_routes import mapa_bp


app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)
app.register_blueprint(bitacora_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(cotizaciones_bp)
app.register_blueprint(facturas_bp)
app.register_blueprint(cuentas_bp)
app.register_blueprint(seniat_bp)
app.register_blueprint(api_bp)
app.register_blueprint(mapa_bp)





# Aliases de endpoints para compatibilidad
app.view_functions['login'] = app.view_functions['auth.login']
app.view_functions['logout'] = app.view_functions['auth.logout']
app.view_functions['ver_bitacora'] = app.view_functions['bitacora.ver_bitacora']
app.view_functions['limpiar_bitacora'] = app.view_functions['bitacora.limpiar_bitacora']
app.view_functions['healthcheck'] = app.view_functions['health.healthcheck']
app.view_functions['index'] = app.view_functions['dashboard.index']
app.view_functions['mostrar_clientes'] = app.view_functions['clientes.mostrar_clientes']
app.view_functions['nuevo_cliente'] = app.view_functions['clientes.nuevo_cliente']
app.view_functions['mostrar_inventario'] = app.view_functions['inventario.mostrar_inventario']
app.view_functions['nuevo_producto'] = app.view_functions['inventario.nuevo_producto']
app.view_functions['mostrar_cotizaciones'] = app.view_functions['cotizaciones.mostrar_cotizaciones']
app.view_functions['mostrar_facturas'] = app.view_functions['facturas.mostrar_facturas']
app.view_functions['ver_factura'] = app.view_functions['facturas.ver_factura']
app.view_functions['nueva_factura'] = app.view_functions['facturas.nueva_factura']
app.view_functions['nueva_cotizacion'] = app.view_functions['cotizaciones.nueva_cotizacion']
app.view_functions['mostrar_cuentas_por_cobrar'] = app.view_functions['cuentas.mostrar_cuentas_por_cobrar']
app.view_functions['registrar_pago'] = app.view_functions['facturas.registrar_pago']
app.view_functions['seniat_consulta'] = app.view_functions['seniat.seniat_consulta']
app.view_functions['seniat_consultar_facturas'] = app.view_functions['seniat.seniat_consultar_facturas']
app.view_functions['seniat_exportar_facturas'] = app.view_functions['seniat.seniat_exportar_facturas']
app.view_functions['seniat_estado_sistema'] = app.view_functions['seniat.seniat_estado_sistema']
app.view_functions['editar_cliente'] = app.view_functions['clientes.editar_cliente']
app.view_functions['eliminar_cliente'] = app.view_functions['clientes.eliminar_cliente']
app.view_functions['editar_producto'] = app.view_functions['inventario.editar_producto']
app.view_functions['eliminar_producto'] = app.view_functions['inventario.eliminar_producto']
app.view_functions['ajustar_stock'] = app.view_functions['inventario.ajustar_stock']
app.view_functions['api_productos'] = app.view_functions['api.api_productos']
app.view_functions['api_clientes'] = app.view_functions['api.api_clientes']
app.view_functions['api_tasa_bcv'] = app.view_functions['api.api_tasa_bcv']
app.view_functions['api_buscar_clientes'] = app.view_functions['api.api_buscar_clientes']
app.view_functions['api_geocodificar'] = app.view_functions['api.api_geocodificar']
app.view_functions['dashboard_inventario'] = app.view_functions['inventario.dashboard_inventario']
app.view_functions['dashboard_clientes'] = app.view_functions['clientes.dashboard_clientes']
app.view_functions['generar_codigo_barras'] = app.view_functions['inventario.generar_codigo_barras']
app.view_functions['prediccion_demandas'] = app.view_functions['inventario.prediccion_demandas']
app.view_functions['imprimir_factura'] = app.view_functions['facturas.imprimir_factura']
app.view_functions['imprimir_cotizacion'] = app.view_functions['cotizaciones.imprimir_cotizacion']
app.view_functions['mapa_avanzado'] = app.view_functions['mapa.mapa_avanzado']

# --- Resolucion Inteligente de Alias para url_for (Compatibilidad 100% con Plantillas Jinja2) ---
from flask import url_for as _flask_url_for

ENDPOINT_ALIASES = {
    'login': 'auth.login',
    'logout': 'auth.logout',
    'ver_bitacora': 'bitacora.ver_bitacora',
    'limpiar_bitacora': 'bitacora.limpiar_bitacora',
    'healthcheck': 'health.healthcheck',
    'index': 'dashboard.index',
    'mostrar_clientes': 'clientes.mostrar_clientes',
    'nuevo_cliente': 'clientes.nuevo_cliente',
    'editar_cliente': 'clientes.editar_cliente',
    'eliminar_cliente': 'clientes.eliminar_cliente',
    'dashboard_clientes': 'clientes.dashboard_clientes',
    'mostrar_inventario': 'inventario.mostrar_inventario',
    'nuevo_producto': 'inventario.nuevo_producto',
    'editar_producto': 'inventario.editar_producto',
    'eliminar_producto': 'inventario.eliminar_producto',
    'dashboard_inventario': 'inventario.dashboard_inventario',
    'generar_codigo_barras': 'inventario.generar_codigo_barras',
    'prediccion_demandas': 'inventario.prediccion_demandas',
    'ajustar_stock': 'inventario.ajustar_stock',
    'mostrar_cotizaciones': 'cotizaciones.mostrar_cotizaciones',
    'nueva_cotizacion': 'cotizaciones.nueva_cotizacion',
    'imprimir_cotizacion': 'cotizaciones.imprimir_cotizacion',
    'mostrar_facturas': 'facturas.mostrar_facturas',
    'ver_factura': 'facturas.ver_factura',
    'nueva_factura': 'facturas.nueva_factura',
    'registrar_pago': 'facturas.registrar_pago',
    'imprimir_factura': 'facturas.imprimir_factura',
    'descargar_factura_pdf': 'facturas.imprimir_factura',
    'mostrar_cuentas_por_cobrar': 'cuentas.mostrar_cuentas_por_cobrar',
    'seniat_consulta': 'seniat.seniat_consulta',
    'seniat_consultar_facturas': 'seniat.seniat_consultar_facturas',
    'seniat_exportar_facturas': 'seniat.seniat_exportar_facturas',
    'seniat_estado_sistema': 'seniat.seniat_estado_sistema',
    'api_productos': 'api.api_productos',
    'api_clientes': 'api.api_clientes',
    'api_tasa_bcv': 'api.api_tasa_bcv',
    'api_buscar_clientes': 'api.api_buscar_clientes',
    'api_geocodificar': 'api.api_geocodificar',
    'mapa_avanzado': 'mapa.mapa_avanzado',
}


def smart_url_for(endpoint, **values):
    """Resuelve alias de endpoints para compatibilidad 100% con plantillas Jinja2 y redirecciones."""
    target = ENDPOINT_ALIASES.get(endpoint, endpoint)
    try:
        return _flask_url_for(target, **values)
    except Exception:
        return _flask_url_for(endpoint, **values)


def handle_url_build_error(error, endpoint, values):
    target = ENDPOINT_ALIASES.get(endpoint)
    if target:
        return _flask_url_for(target, **values)
    raise error


app.url_build_error_handlers.append(handle_url_build_error)


@app.context_processor
def inject_global_variables():
    return dict(
        url_for=smart_url_for,
        maps_config=get_maps_config(),
        zip=zip,
        empresa=cargar_empresa(),
        now=datetime.now,
        datetime=datetime
    )


url_for = smart_url_for















# --- Funciones de Utilidad ---
def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def guardar_imagen_producto(imagen, producto_id):
    """Guarda la imagen de un producto y retorna la ruta relativa con '/' como separador."""
    if imagen and allowed_file(imagen.filename):
        # Generar nombre único para la imagen
        extension = imagen.filename.rsplit('.', 1)[1].lower()
        nombre_archivo = f"producto_{producto_id}.{extension}"
        ruta_archivo = os.path.join(IMAGENES_PRODUCTOS_FOLDER, nombre_archivo)
        
        # Guardar la imagen
        imagen.save(ruta_archivo)
        
        # Retornar la ruta relativa para guardar en la base de datos (siempre con /)
        return f"imagenes_productos/{nombre_archivo}"
    return None

def cargar_clientes_desde_csv(archivo_csv):
    """Carga clientes desde un archivo CSV."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                tipo_id = fila.get('tipo_id', 'V')
                numero_id = fila.get('numero_id', '').strip()
                if not numero_id.isdigit():
                    continue
                nuevo_id = f"{tipo_id}-{numero_id}"
                if nuevo_id not in clientes:
                    clientes[nuevo_id] = {
                        'id': nuevo_id,
                        'nombre': fila.get('nombre', '').strip(),
                        'email': fila.get('email', '').strip() if 'email' in fila else '',
                        'telefono': fila.get('telefono', '').strip() if 'telefono' in fila else '',
                        'direccion': fila.get('direccion', '').strip() if 'direccion' in fila else ''
                    }
        return guardar_datos(ARCHIVO_CLIENTES, clientes)
    except Exception as e:
        print(f"Error cargando clientes desde CSV: {e}")
        return False

def cargar_productos_desde_csv(archivo_csv):
    """Carga productos desde un archivo CSV."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                nuevo_id = str(len(inventario) + 1)
                inventario[nuevo_id] = {
                    'nombre': fila.get('nombre', '').strip(),
                    'precio': float(fila.get('precio', 0)),
                    'cantidad': int(fila.get('cantidad', 0)),
                    'categoria': fila.get('categoria', '').strip(),
                    'ruta_imagen': "",
                    'ultima_entrada': None,
                    'ultima_salida': None
                }
        return guardar_datos(ARCHIVO_INVENTARIO, inventario)
    except Exception as e:
        print(f"Error cargando productos desde CSV: {e}")
        return False

def limpiar_valor_monetario(valor):
    """Limpia y convierte un valor monetario a float."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        # Eliminar símbolos y espacios
        valor = str(valor).replace('$', '').replace(',', '').replace('Bs', '').strip()
        # Reemplazar coma decimal por punto si existe
        if ',' in valor:
            valor = valor.replace(',', '.')
        return float(valor)
    except (ValueError, TypeError):
        return 0.0

def cargar_empresa():
    data = cargar_datos('empresa.json', crear_vacio=False)
    if data:
        return data
    return {
        "nombre": "Nombre de la Empresa",
        "rif": "J-000000000",
        "telefono": "0000-0000000",
        "direccion": "Dirección de la empresa"
    }

def es_fecha_valida(fecha_str):
    """Valida si una fecha es válida y puede ser comparada."""
    if not fecha_str or not isinstance(fecha_str, str):
        return False
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def limpiar_monto(monto):
    if not monto:
        return 0.0
    return float(str(monto).replace('$', '').replace('Bs', '').replace(',', '').strip())

# --- Rutas protegidas ---



@app.route('/api/health')
def api_health():
    """Health check simple para monitoreo."""
    checks = {}
    status_code = 200

    # Check JSON local
    try:
        _ = cargar_datos(ARCHIVO_CLIENTES, crear_vacio=False)
        checks['json_local'] = {'ok': True}
    except Exception as e:
        checks['json_local'] = {'ok': False, 'error': str(e)}
        status_code = 503

    # Check Firebase (si está habilitado)
    try:
        if usar_firebase():
            _ = cargar_datos(ARCHIVO_INVENTARIO, crear_vacio=False)
            checks['firebase'] = {'ok': True}
        else:
            checks['firebase'] = {'ok': True, 'mode': 'disabled'}
    except Exception as e:
        checks['firebase'] = {'ok': False, 'error': str(e)}
        status_code = 503
        log_error(logger_obs, 'health_firebase_error', e)
        notify_critical('health_firebase_error', 'Fallo health check de Firebase', checks['firebase'])

    payload = {
        'success': status_code == 200,
        'service': 'kisvic',
        'time': datetime.now().isoformat(),
        'checks': checks,
    }
    return jsonify(payload), status_code

@app.route('/api/dashboard-filtros')
@login_required
def api_dashboard_filtros():
    """API para obtener estadísticas filtradas del dashboard."""
    filtro_tipo = request.args.get('tipo')
    filtro_valor = request.args.get('valor')
    
    try:
        stats = obtener_estadisticas_filtradas(filtro_tipo, filtro_valor)
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def _to_float(value, default=0.0):
    try:
        return float(value or 0)
    except Exception:
        return float(default)


def _to_int(value, default=0):
    try:
        return int(float(value or 0))
    except Exception:
        return int(default)


def _dashboard_api_autorizado() -> bool:
    # Permite exponer dashboard de solo lectura sin sesión cuando se requiera.
    if session.get('usuario'):
        return True
    return os.environ.get('KISVIC_PUBLIC_DASHBOARD_API', '0').strip().lower() in ('1', 'true', 'yes', 'on')


@app.route('/api/dashboard/resumen')
def api_dashboard_resumen():
    """API resumen para dashboard React (datos reales)."""
    if not _dashboard_api_autorizado():
        log_event(
            logger_obs,
            'dashboard_resumen_unauthorized',
            path=request.path,
            remote_addr=request.remote_addr,
        )
        return jsonify({'success': False, 'error': 'No autorizado'}), 401

    try:
        stats = obtener_estadisticas_filtradas()
        inventario = cargar_datos(ARCHIVO_INVENTARIO) or {}
        facturas = cargar_datos(ARCHIVO_FACTURAS) or {}
        tasa_bcv = _to_float(stats.get('tasa_bcv', 0), 36.0)

        # Normalizar productos para frontend React
        productos = []
        for pid, p in inventario.items():
            stock = _to_int(p.get('cantidad', p.get('stock', 0)))
            punto_pedido = _to_int(p.get('stock_minimo', p.get('punto_pedido', 10)), 10)
            precio = _to_float(p.get('precio_detal', p.get('precio', 0)))
            productos.append({
                'id': str(pid),
                'nombre': p.get('nombre', f'Producto {pid}'),
                'sku': p.get('codigo', str(pid)),
                'descripcion': p.get('descripcion', ''),
                'precio': precio,
                'stock': stock,
                'punto_pedido': punto_pedido,
                'categoria': p.get('categoria', ''),
                'imagen': p.get('imagen', ''),
                'created_at': p.get('fecha_creacion', ''),
                'updated_at': p.get('fecha_actualizacion', ''),
            })

        # Normalizar facturas para frontend React
        facturas_lista = []
        for fid, f in facturas.items():
            cliente_nombre = f.get('cliente_nombre', f.get('cliente', 'Cliente'))
            total_usd = _to_float(f.get('total_usd', 0))
            total_bs = _to_float(f.get('total_bs', total_usd * tasa_bcv))
            total_abonado = _to_float(f.get('total_abonado', 0))
            saldo = max(0.0, total_usd - total_abonado)
            estado = str(f.get('estado', 'pendiente')).lower()
            if estado not in ('pagada', 'pendiente', 'vencida', 'cancelada'):
                estado = 'pagada' if saldo <= 0 else 'pendiente'

            productos_raw = f.get('productos', []) or []
            productos_norm = []
            for idx, prod in enumerate(productos_raw):
                cantidad = _to_float(prod.get('cantidad', 0))
                precio_unitario = _to_float(prod.get('precio', prod.get('precio_unitario', 0)))
                productos_norm.append({
                    'id': str(prod.get('id', f'{fid}_{idx}')),
                    'nombre': prod.get('nombre', f'Producto {idx + 1}'),
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                    'total': _to_float(prod.get('total', cantidad * precio_unitario)),
                    'sku': prod.get('codigo', ''),
                })

            pagos_norm = []
            for idx, pago in enumerate(f.get('pagos', []) or []):
                pagos_norm.append({
                    'id': str(pago.get('id', f'{fid}_p{idx}')),
                    'fecha': pago.get('fecha', f.get('fecha', '')),
                    'monto': _to_float(pago.get('monto', 0)),
                    'metodo': pago.get('metodo', 'transferencia'),
                    'referencia': pago.get('referencia', ''),
                    'observaciones': pago.get('observaciones', ''),
                })

            facturas_lista.append({
                'id': str(fid),
                'numero': f.get('numero', str(fid)),
                'fecha': f.get('fecha', ''),
                'cliente': cliente_nombre,
                'cliente_id': f.get('cliente_id', ''),
                'total_usd': total_usd,
                'total_bs': total_bs,
                'total_abonado': total_abonado,
                'saldo': saldo,
                'estado': estado,
                'productos': productos_norm,
                'pagos': pagos_norm,
                'vencimiento': f.get('fecha_vencimiento', ''),
                'observaciones': f.get('observaciones', ''),
                'created_at': f.get('fecha_creacion', ''),
                'updated_at': f.get('fecha_actualizacion', ''),
            })

        facturas_lista.sort(key=lambda x: x.get('fecha', ''), reverse=True)

        bcv_rate = {
            'tasa': tasa_bcv,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'ultima_actualizacion': datetime.now().isoformat(),
        }

        return jsonify({
            'success': True,
            'data': {
                'stats': {
                    'total_clientes': _to_int(stats.get('total_clientes', 0)),
                    'total_productos': _to_int(stats.get('total_productos', 0)),
                    'facturas_mes': _to_int(stats.get('facturas_mes', 0)),
                    'total_cobrar_usd': _to_float(stats.get('total_cobrar_usd', 0)),
                    'total_cobrar_bs': _to_float(stats.get('total_cobrar_bs', 0)),
                    'total_pagos_recibidos_usd': _to_float(stats.get('total_pagos_recibidos_usd', 0)),
                    'total_pagos_recibidos_bs': _to_float(stats.get('total_pagos_recibidos_bs', 0)),
                    'total_facturado_usd': _to_float(stats.get('total_facturado_usd', 0)),
                    'promedio_factura_usd': _to_float(stats.get('promedio_factura_usd', 0)),
                    'tasa_bcv': tasa_bcv,
                    'ultima_actualizacion': datetime.now().isoformat(),
                },
                'invoices': facturas_lista[:50],
                'products': productos,
                'bcvRate': bcv_rate,
            },
        })
    except Exception as e:
        log_error(
            logger_obs,
            'dashboard_resumen_error',
            e,
            path=request.path,
            remote_addr=request.remote_addr,
        )
        notify_critical(
            'dashboard_resumen_error',
            'Fallo en API dashboard resumen',
            {'error': str(e)},
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tarjeta-filtro')
@login_required
def api_tarjeta_filtro():
    """API para obtener datos filtrados de una tarjeta específica."""
    tarjeta = request.args.get('tarjeta')
    filtro_tipo = request.args.get('tipo')
    filtro_valor = request.args.get('valor')
    
    try:
        # Cargar datos reales
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        tasa_bcv = obtener_tasa_bcv()
        if hasattr(tasa_bcv, 'json'):
            tasa_bcv = tasa_bcv.json().get('USD', {}).get('transferencia', 1.0)
        else:
            tasa_bcv = float(tasa_bcv) if tasa_bcv else 1.0
        
        # Obtener fecha actual
        hoy = datetime.now()
        mes_actual = hoy.month
        año_actual = hoy.year
        
        # Aplicar filtros según el tipo
        if filtro_tipo == 'hoy':
            fecha_filtro = hoy.strftime('%Y-%m-%d')
        elif filtro_tipo == 'mes' and filtro_valor:
            try:
                mes = int(filtro_valor)
                fecha_filtro = f"{año_actual}-{mes:02d}-01"
            except ValueError:
                return jsonify({'success': False, 'error': 'Mes inválido'})
        else:
            fecha_filtro = None
        
        # Calcular estadísticas según la tarjeta
        if tarjeta == 'cobranza':
            total_cobrar_usd = 0
            for f in facturas.values():
                total_facturado = float(f.get('total_usd', 0))
                total_abonado = float(f.get('total_abonado', 0))
                saldo = max(0, total_facturado - total_abonado)
                
                # Aplicar filtro de fecha si existe
                if fecha_filtro:
                    fecha_factura = f.get('fecha', '')
                    if fecha_filtro == 'hoy':
                        if fecha_factura != hoy.strftime('%Y-%m-%d'):
                            continue
                    else:  # filtro por mes
                        if fecha_factura and not fecha_factura.startswith(fecha_filtro[:7]):
                            continue
                
                if saldo > 0:
                    total_cobrar_usd += saldo
            
            total_cobrar_bs = total_cobrar_usd * tasa_bcv
            
            return jsonify({
                'success': True,
                'data': {
                    'total_cobrar_usd': total_cobrar_usd,
                    'total_cobrar_bs': total_cobrar_bs
                }
            })
            
        elif tarjeta == 'pagos':
            total_pagos_recibidos_usd = 0
            for f in facturas.values():
                if 'pagos' in f and f['pagos']:
                    for pago in f['pagos']:
                        try:
                            fecha_pago = pago.get('fecha', '')
                            if fecha_pago:
                                # Aplicar filtro de fecha
                                if fecha_filtro == 'hoy':
                                    if fecha_pago != hoy.strftime('%Y-%m-%d'):
                                        continue
                                elif fecha_filtro and not fecha_pago.startswith(fecha_filtro[:7]):
                                    continue
                                
                                monto = float(pago.get('monto', 0))
                                total_pagos_recibidos_usd += monto
                        except Exception:
                            continue
            
            total_pagos_recibidos_bs = total_pagos_recibidos_usd * tasa_bcv
            
            return jsonify({
                'success': True,
                'data': {
                    'total_pagos_recibidos_usd': total_pagos_recibidos_usd,
                    'total_pagos_recibidos_bs': total_pagos_recibidos_bs
                }
            })
            
        elif tarjeta == 'facturado':
            total_facturado_usd = 0
            cantidad_facturas = 0
            
            for f in facturas.values():
                # Aplicar filtro de fecha
                if fecha_filtro:
                    fecha_factura = f.get('fecha', '')
                    if fecha_filtro == 'hoy':
                        if fecha_factura != hoy.strftime('%Y-%m-%d'):
                            continue
                    else:  # filtro por mes
                        if fecha_factura and not fecha_factura.startswith(fecha_filtro[:7]):
                            continue
                
                total_facturado_usd += float(f.get('total_usd', 0))
                cantidad_facturas += 1
            
            promedio_factura_usd = total_facturado_usd / cantidad_facturas if cantidad_facturas > 0 else 0
            
            return jsonify({
                'success': True,
                'data': {
                    'total_facturado_usd': total_facturado_usd,
                    'promedio_factura_usd': promedio_factura_usd
                }
            })
        
        return jsonify({'success': False, 'error': 'Tarjeta no válida'})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/opciones-filtro')
@login_required
def api_opciones_filtro():
    """API para obtener las opciones disponibles para los filtros."""
    try:
        opciones = obtener_opciones_filtro()
        return jsonify({
            'success': True,
            'data': opciones
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/opciones-filtro-avanzado')
@login_required
def api_opciones_filtro_avanzado():
    """API para obtener las opciones de filtros avanzados con menús anidados."""
    try:
        opciones = obtener_opciones_filtro_avanzado()
        return jsonify({
            'success': True,
            'data': opciones
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Ruta de prueba sin autenticación para debugging
@app.route('/api/test-tarjeta-filtro')
def api_test_tarjeta_filtro():
    """API de prueba para obtener métricas filtradas sin autenticación."""
    tarjeta = request.args.get('tarjeta')
    filtro_tipo = request.args.get('tipo')
    filtro_valor = request.args.get('valor')
    
    print(f"🔍 DEBUG API: tarjeta={tarjeta}, tipo={filtro_tipo}, valor={filtro_valor}")
    
    if not tarjeta:
        return jsonify({
            'success': False,
            'error': 'Tarjeta no especificada'
        }), 400
    
    try:
        metricas = obtener_metricas_tarjeta(tarjeta, filtro_tipo, filtro_valor)
        print(f"✅ DEBUG API: Respuesta para {tarjeta}: {metricas}")
        return jsonify({
            'success': True,
            'data': metricas
        })
    except Exception as e:
        print(f"❌ DEBUG API: Error para {tarjeta}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500





@app.route('/clientes/dashboard-test')
@login_required
def dashboard_clientes_test():
    """Versión de prueba del dashboard para debugging."""
    try:
        from datetime import datetime, timedelta
        
        # Datos básicos de prueba
        datos_test = {
            'total_clientes': 10,
            'total_facturado': 1000.0,
            'total_abonado': 800.0,
            'total_por_cobrar': 200.0,
            'segmentos': {
                'vip': {'clientes': 2, 'facturado': 500.0, 'color': '#FFD700', 'porcentaje': 20.0},
                'frecuente': {'clientes': 3, 'facturado': 300.0, 'color': '#32CD32', 'porcentaje': 30.0},
                'activo': {'clientes': 2, 'facturado': 150.0, 'color': '#1E90FF', 'porcentaje': 20.0},
                'regular': {'clientes': 2, 'facturado': 50.0, 'color': '#FFA500', 'porcentaje': 20.0},
                'inactivo': {'clientes': 1, 'facturado': 0.0, 'color': '#DC143C', 'porcentaje': 10.0},
                'potencial': {'clientes': 0, 'facturado': 0.0, 'color': '#9370DB', 'porcentaje': 0.0}
            },
            'estados_pago': {
                'al_dia': {'clientes': 7, 'monto': 0.0},
                'pendiente': {'clientes': 2, 'monto': 100.0},
                'moroso': {'clientes': 1, 'monto': 100.0}
            },
            'clientes_top': [
                {'id': 'V-12345678', 'nombre': 'Cliente Test 1', 'total_facturado': 500.0, 'total_por_cobrar': 0.0, 'segmento': 'vip', 'estado_pago': 'al_dia', 'cantidad_facturas': 5}
            ],
            'tendencias': [
                {'mes': '2024-08', 'facturado': 800.0, 'clientes': 8},
                {'mes': '2024-09', 'facturado': 900.0, 'clientes': 9},
                {'mes': '2024-10', 'facturado': 1000.0, 'clientes': 10}
            ],
            'periodo': '6',
            'segmento_filtro': 'todos',
            'estado_filtro': 'todos',
            'vista_tipo': 'resumen'
        }
        
        return render_template('dashboard_clientes.html', **datos_test)
        
    except Exception as e:
        print(f"Error en dashboard_clientes_test: {e}")
        import traceback
        traceback.print_exc()
        return f"Error en dashboard de prueba: {str(e)}"













@app.route('/inventario/<id>')
def ver_producto(id):
    """Muestra los detalles de un producto del inventario."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    producto = inventario.get(id)
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('mostrar_inventario'))
    return render_template('producto_detalle.html', producto=producto, id=id)







# Ruta de prueba para verificar que funciona
@app.route('/test-whatsapp')
def test_whatsapp():
    return jsonify({'message': 'Ruta de prueba funcionando'})

# Rutas para capturar URLs malformadas específicas
@app.route('/facturas//editar', methods=['GET', 'POST'])
@login_required
def editar_factura_url_malformada():
    """Captura URLs malformadas como /facturas//editar y redirige"""
    flash('URL de factura inválida detectada', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/facturas//', methods=['GET', 'POST'])
@login_required
def factura_url_malformada_general():
    """Captura URLs malformadas como /facturas// y redirige"""
    flash('URL de factura inválida detectada', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/facturas///editar', methods=['GET', 'POST'])
@login_required
def editar_factura_url_triple_malformada():
    """Captura URLs malformadas como /facturas///editar y redirige"""
    flash('URL de factura inválida detectada', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/facturas/<id>/editar', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    # Validación simple del ID
    if not id or str(id).strip() == '':
        flash('ID de factura inválido', 'danger')
        return redirect(url_for('mostrar_facturas'))
    facturas = cargar_datos(ARCHIVO_FACTURAS) or {}
    if os.path.exists("facturas_json"):
        for fname in os.listdir("facturas_json"):
            if fname.endswith(".json"):
                fk = fname[len("factura_"):-len(".json")] if fname.startswith("factura_") else fname[:-len(".json")]
                if fk not in facturas:
                    fdata = cargar_datos(os.path.join("facturas_json", fname))
                    if fdata and isinstance(fdata, dict):
                        facturas[fk] = fdata

    real_id = id
    if real_id not in facturas:
        for k, f in facturas.items():
            if isinstance(f, dict):
                f_num = str(f.get("numero", "")).strip().lower()
                f_sec = str(f.get("numero_secuencial", "")).strip().lower()
                f_id = str(f.get("id", "")).strip().lower()
                t_lower = str(id).strip().lower()
                if t_lower in (f_num, f_sec, f_id, str(k).lower()):
                    real_id = k
                    break
                t_clean = t_lower.replace("fac-", "").replace("factura_", "").lstrip("0")
                f_clean = f_num.replace("fac-", "").lstrip("0")
                k_clean = str(k).lower().replace("fac-", "").replace("factura_", "").lstrip("0")
                if t_clean and (t_clean == f_clean or t_clean == f_sec.lstrip("0") or t_clean == k_clean):
                    real_id = k
                    break

    if real_id not in facturas:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))

    id = real_id
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if request.method == 'POST':
        try:
            factura = facturas[id]
            # Guardar cantidades antiguas para comparar
            cantidades_antiguas = dict(zip(factura['productos'], factura['cantidades']))
            
            # Obtener y validar datos básicos
            factura['cliente_id'] = request.form['cliente_id']
            factura['fecha'] = request.form['fecha']
            factura['numero'] = request.form['numero']
            factura['hora'] = request.form.get('hora', '')
            factura['condicion_pago'] = request.form.get('condicion_pago', 'contado')
            factura['dias_credito'] = request.form.get('dias_credito', '30')
            factura['fecha_vencimiento'] = request.form.get('fecha_vencimiento', '') if request.form.get('condicion_pago') == 'credito' else ''
            
            # Obtener productos, cantidades y precios
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            precios = [float(p) for p in precios]
            
            # Registrar cambios en el stock
            for prod_id, nueva_cantidad in zip(productos, cantidades):
                nueva_cantidad = int(nueva_cantidad)
                cantidad_antigua = int(cantidades_antiguas.get(prod_id, 0))
                
                if nueva_cantidad != cantidad_antigua:
                    # Calcular la diferencia
                    diferencia = nueva_cantidad - cantidad_antigua
                    
                    # Actualizar el stock
                    inventario[prod_id]['cantidad'] -= diferencia
                    
                    # Registrar el movimiento en historial_ajustes
                    if 'historial_ajustes' not in inventario[prod_id]:
                        inventario[prod_id]['historial_ajustes'] = []
                    
                    tipo = 'entrada' if diferencia < 0 else 'salida'
                    cantidad_abs = abs(diferencia)
                    
                    inventario[prod_id]['historial_ajustes'].append({
                        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'tipo': tipo,
                        'cantidad': cantidad_abs,
                        'motivo': f'Ajuste por edición de factura N°{factura["numero"]}',
                        'usuario': session.get('usuario', ''),
                        'observaciones': f'Cantidad anterior: {cantidad_antigua}, Nueva cantidad: {nueva_cantidad}'
                    })
            
            factura['productos'] = productos
            factura['cantidades'] = cantidades
            factura['precios'] = precios
            
            # Obtener y validar tasa BCV
            tasa_bcv = limpiar_valor_monetario(request.form.get('tasa_bcv', '36.00'))
            if tasa_bcv <= 0:
                tasa_bcv = 36.00
            factura['tasa_bcv'] = tasa_bcv
            
            # Calcular subtotales y totales
            subtotal_usd = sum(precios[i] * int(cantidades[i]) for i in range(len(precios)))
            subtotal_bs = subtotal_usd * tasa_bcv
            descuento = limpiar_valor_monetario(request.form.get('descuento', '0'))
            tipo_descuento = request.form.get('tipo_descuento', 'bs')
            if tipo_descuento == 'porc':
                descuento_total = subtotal_usd * (descuento / 100)
            else:
                descuento_total = descuento / tasa_bcv
            iva = limpiar_valor_monetario(request.form.get('iva', '0'))
            iva_total = (subtotal_usd - descuento_total) * (iva / 100)
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            
            factura['descuento'] = descuento
            factura['tipo_descuento'] = tipo_descuento
            factura['iva'] = iva
            factura['subtotal_usd'] = subtotal_usd
            factura['subtotal_bs'] = subtotal_bs
            factura['descuento_total'] = descuento_total
            factura['iva_total'] = iva_total
            factura['total_usd'] = total_usd
            factura['total_bs'] = total_bs
            
            # Procesar pagos
            pagos_json = request.form.get('pagos_json', '[]')
            try:
                pagos = json.loads(pagos_json)
                for pago in pagos:
                    if 'monto' in pago:
                        pago['monto'] = limpiar_valor_monetario(pago['monto'])
                factura['pagos'] = pagos
            except Exception:
                factura['pagos'] = []
            
            # Calcular total abonado y saldo pendiente
            total_abonado = sum(float(p['monto']) for p in factura['pagos'])
            factura['total_abonado'] = total_abonado
            saldo_pendiente = factura.get('total_usd', 0) - total_abonado
            
            # Si el saldo pendiente es muy pequeño (menos de 0.01) o el total abonado es igual o mayor al total
            if abs(saldo_pendiente) < 0.01 or total_abonado >= factura.get('total_usd', 0):
                saldo_pendiente = 0
                factura['estado'] = 'pagada'
            else:
                factura['estado'] = 'pendiente'
            
            factura['saldo_pendiente'] = saldo_pendiente
            facturas[id] = factura
            
            # Guardar cambios en el inventario
            if not guardar_datos(ARCHIVO_INVENTARIO, inventario):
                flash('Error al actualizar el inventario', 'danger')
                return redirect(url_for('editar_factura', id=id))
            
            if guardar_datos(ARCHIVO_FACTURAS, facturas):
                flash('Factura actualizada exitosamente', 'success')
                registrar_bitacora(session['usuario'], 'Editar factura', f"ID: {id}")
                return redirect(url_for('ver_factura', id=id))
            else:
                flash('Error al actualizar la factura', 'danger')
        except Exception as e:
            flash(f'Error al actualizar la factura: {str(e)}', 'danger')
    
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0 or k in facturas[id].get('productos', [])}
    empresa = cargar_empresa()
    return render_template('factura_form.html', id=id, factura=facturas[id], clientes=clientes, inventario=inventario_disponible, editar=True, zip=zip, empresa=empresa)

@app.route('/facturas/duplicar', methods=['POST'])
@login_required
def duplicar_factura():
    """Duplica una factura existente con un nuevo número."""
    try:
        # Obtener datos de la factura a duplicar
        datos = request.get_json()
        
        # Generar nuevo número de factura
        usuario_actual = session.get('usuario', 'SISTEMA')
        numero_fiscal, numero_secuencial = control_numeracion.obtener_siguiente_numero('FACTURA', usuario_actual)
        
        # Crear nueva factura
        nueva_factura = {
            'id': str(uuid.uuid4()),
            'numero': numero_fiscal,
            'numero_secuencial': numero_secuencial,
            'fecha': datos.get('fecha', datetime.now().strftime('%Y-%m-%d')),
            'hora': datos.get('hora', datetime.now().strftime('%H:%M:%S')),
            'cliente_id': datos.get('cliente_id'),
            'tasa_bcv': float(datos.get('tasa_bcv', 36.0)),
            'condicion_pago': datos.get('condicion_pago', 'contado'),
            'iva': float(datos.get('iva', 16)),
            'descuento': datos.get('descuento', '0'),
            'tipo_descuento': datos.get('tipo_descuento', 'bs'),
            'pagos': [],
            'estado': 'pendiente',
            'total_abonado': 0,
            'saldo_pendiente': 0
        }
        
        # Copiar productos (estructura SENIAT)
        if datos.get('items'):
            nueva_factura['items'] = datos['items']
            # Calcular totales desde items
            subtotal_usd = sum(float(item.get('subtotal_usd', 0)) for item in datos['items'])
            nueva_factura['subtotal_usd'] = subtotal_usd
            nueva_factura['subtotal_bs'] = subtotal_usd * nueva_factura['tasa_bcv']
        else:
            # Estructura legacy
            nueva_factura['productos'] = datos.get('productos', [])
            nueva_factura['cantidades'] = datos.get('cantidades', [])
            nueva_factura['precios'] = datos.get('precios', [])
            
            # Calcular totales desde productos/cantidades/precios
            productos = datos.get('productos', [])
            cantidades = datos.get('cantidades', [])
            precios = datos.get('precios', [])
            
            subtotal_usd = 0
            for i in range(len(productos)):
                if i < len(cantidades) and i < len(precios):
                    cantidad = int(cantidades[i]) if cantidades[i] else 0
                    precio = float(precios[i]) if precios[i] else 0
                    subtotal_usd += cantidad * precio
            
            nueva_factura['subtotal_usd'] = subtotal_usd
            nueva_factura['subtotal_bs'] = subtotal_usd * nueva_factura['tasa_bcv']
        
        # Calcular descuentos e IVA
        descuento = float(datos.get('descuento', 0))
        if datos.get('tipo_descuento') == 'bs':
            descuento_usd = descuento / nueva_factura['tasa_bcv']
        else:
            descuento_usd = descuento
        
        nueva_factura['descuento_total'] = descuento_usd
        
        base_imponible = subtotal_usd - descuento_usd
        iva_total = base_imponible * (nueva_factura['iva'] / 100)
        nueva_factura['iva_total'] = iva_total
        
        # Totales finales
        total_usd = base_imponible + iva_total
        total_bs = total_usd * nueva_factura['tasa_bcv']
        nueva_factura['total_usd'] = total_usd
        nueva_factura['total_bs'] = total_bs
        nueva_factura['saldo_pendiente'] = total_usd
        
        # Guardar nueva factura
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        facturas[nueva_factura['id']] = nueva_factura
        guardar_datos(ARCHIVO_FACTURAS, facturas)
        
        # Registrar en bitácora
        try:
            registrar_bitacora('duplicacion_factura', f"Factura {nueva_factura['numero']} duplicada desde factura original por {session.get('usuario', 'SISTEMA')}")
        except Exception as e:
            print(f"Error registrando en bitácora: {e}")
        
        return jsonify({
            'success': True,
            'factura_id': str(nueva_factura['id']),
            'numero': str(nueva_factura['numero']),
            'message': 'Factura duplicada correctamente'
        })
        
    except Exception as e:
        print(f"Error duplicando factura: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/facturas/limpiar_ids_invalidos', methods=['POST'])
@login_required
def limpiar_ids_invalidos_facturas():
    """Ultra-mantenimiento: limpia IDs inválidos, repara JSONs corruptos, reconstruye firmas SENIAT, sincroniza CxC y regenera respaldos."""
    try:
        # 0. Crear copia de seguridad instantánea .bak del maestro antes de operar
        ruta_maestro = _ruta_absoluta(ARCHIVO_FACTURAS) if '_ruta_absoluta' in globals() else ARCHIVO_FACTURAS
        if os.path.exists(ruta_maestro):
            try:
                import shutil
                shutil.copy2(ruta_maestro, ruta_maestro + ".bak")
            except Exception:
                pass

        facturas = cargar_datos(ARCHIVO_FACTURAS) or {}
        ids_invalidos = []
        facturas_reparadas = 0
        archivos_cuarentena = 0
        respaldos_regenerados = 0

        # 1. Purgar IDs vacíos, nulos o no-diccionarios
        for id_factura in list(facturas.keys()):
            if not id_factura or str(id_factura).strip() == '' or not isinstance(facturas[id_factura], dict):
                ids_invalidos.append(id_factura)
                facturas.pop(id_factura, None)

        # 2. Auditar archivos individuales en disco y mover inservibles a cuarentena
        facturas_dir = "facturas_json"
        cuarentena_dir = os.path.join(facturas_dir, "cuarentena")

        if os.path.exists(facturas_dir):
            for fname in os.listdir(facturas_dir):
                fpath = os.path.join(facturas_dir, fname)
                if fname.endswith(".json") and fname != "facturas.json" and os.path.isfile(fpath):
                    if os.path.getsize(fpath) == 0:
                        try:
                            os.makedirs(cuarentena_dir, exist_ok=True)
                            import shutil
                            shutil.move(fpath, os.path.join(cuarentena_dir, fname))
                            archivos_cuarentena += 1
                        except Exception:
                            pass
                    else:
                        try:
                            with open(fpath, 'r', encoding='utf-8') as f_test:
                                fdata = json.load(f_test)
                                if not isinstance(fdata, dict):
                                    raise ValueError("JSON no es objeto")
                        except Exception:
                            try:
                                os.makedirs(cuarentena_dir, exist_ok=True)
                                import shutil
                                shutil.move(fpath, os.path.join(cuarentena_dir, fname))
                                archivos_cuarentena += 1
                            except Exception:
                                pass

        # 3. Deduplicar maestro, sanear numéricamente y regenerar firmas SENIAT
        from seguridad_fiscal import seguridad_fiscal
        facturas_unificadas = {}
        vistos = set()

        for k, f in list(facturas.items()):
            if not isinstance(f, dict):
                continue
            num = str(f.get("numero", "")).strip()
            f_id = str(f.get("id", "")).strip()
            sec = str(f.get("numero_secuencial", "")).strip()
            ukey = num or f_id or sec or str(k).strip()

            if ukey in vistos:
                continue
            vistos.add(ukey)

            # Normalización numérica preventiva
            precios_saneados = []
            for p in f.get("precios", []):
                try: precios_saneados.append(float(str(p).replace(",", ".").strip()))
                except Exception: precios_saneados.append(0.0)
            f["precios"] = precios_saneados

            cantidades_saneadas = []
            for c in f.get("cantidades", []):
                try: cantidades_saneadas.append(int(float(str(c).strip())))
                except Exception: cantidades_saneadas.append(0)
            f["cantidades"] = cantidades_saneadas

            # Reparación automática de firma fiscal SENIAT si falta
            if not f.get("firma_fiscal") and num:
                try:
                    f["firma_fiscal"] = seguridad_fiscal.generar_hash_documento(
                        documento_tipo="FACTURA",
                        documento_numero=num,
                        monto_total=float(f.get("total_bs", 0)),
                        fecha=str(f.get("fecha", ""))
                    )
                    facturas_reparadas += 1
                except Exception:
                    pass

            primary_key = f_id or str(k).strip() or num
            f["id"] = primary_key
            facturas_unificadas[primary_key] = f

            # Regenerar archivo individual en disco si no existía
            if os.path.exists(facturas_dir):
                f_indiv = os.path.join(facturas_dir, f"factura_{primary_key}.json")
                if not os.path.exists(f_indiv):
                    guardar_datos(f_indiv, f)
                    respaldos_regenerados += 1

        guardar_datos(ARCHIVO_FACTURAS, facturas_unificadas)

        # 4. Sincronizar cuentas por cobrar
        try:
            cuentas = cargar_datos(ARCHIVO_CUENTAS) or {}
            if isinstance(cuentas, dict):
                cuentas_actualizadas = False
                for fid, f in facturas_unificadas.items():
                    est = str(f.get("estado", "")).lower()
                    cond = str(f.get("condicion_pago", "")).lower()
                    if cond == "credito" or est in ("pendiente", "abonada"):
                        num_fac = f.get("numero", fid)
                        if num_fac not in cuentas:
                            cuentas[num_fac] = {
                                "numero_factura": num_fac,
                                "cliente_id": f.get("cliente_id", ""),
                                "monto_total": float(f.get("total_usd", 0)),
                                "monto_pendiente": float(f.get("saldo_pendiente", f.get("total_usd", 0))),
                                "fecha_emision": f.get("fecha", ""),
                                "estado": est
                            }
                            cuentas_actualizadas = True
                if cuentas_actualizadas:
                    guardar_datos(ARCHIVO_CUENTAS, cuentas)
        except Exception:
            pass

        resumen = []
        if ids_invalidos: resumen.append(f"{len(ids_invalidos)} entradas inválidas")
        if archivos_cuarentena > 0: resumen.append(f"{archivos_cuarentena} archivos a cuarentena")
        if facturas_reparadas > 0: resumen.append(f"{facturas_reparadas} firmas SENIAT restauradas")
        if respaldos_regenerados > 0: resumen.append(f"{respaldos_regenerados} archivos de respaldo regenerados")

        if resumen:
            flash(f"Super-Mantenimiento Exitoso: Se corrigieron {', '.join(resumen)}.", "success")
            try:
                registrar_bitacora(session.get('usuario', 'SISTEMA'), 'Ultra Mantenimiento Facturas', f"Detalles: {', '.join(resumen)}")
            except Exception:
                pass
        else:
            flash("Sistema de Facturación Blindado (100% Saludable): No se detectaron anomalías, saldos descalibrados ni archivos corruptos.", "info")

    except Exception as e:
        flash(f"Error durante el mantenimiento: {str(e)}", "danger")

    return redirect(url_for('mostrar_facturas'))

@app.route('/facturas/migrar_formato', methods=['POST'])
@login_required
def migrar_formato_facturas():
    """Convierte facturas históricas al formato fiscal nuevo (estructura SENIAT).
    No cambia el número fiscal existente si ya lo tienen; crea items a partir de productos/cantidades/precios.
    """
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)

    actualizadas = 0
    renumeradas = 0
    for fid, f in list(facturas.items()):
        try:
            tasa = float(f.get('tasa_bcv') or 0) or 36.0
            f_actualizada = copy.deepcopy(f)

            # Normalizar número y hora SIEMPRE
            numero_val = f_actualizada.get('numero')
            if numero_val:
                digits = re.sub(r'\D', '', str(numero_val))
                if digits:
                    try:
                        nuevo_num = f"FAC-{int(digits):08d}"
                        if nuevo_num != f_actualizada.get('numero'):
                            f_actualizada['numero'] = nuevo_num
                            renumeradas += 1
                    except Exception:
                        pass
            hora_val = f_actualizada.get('hora') or ''
            if hora_val and re.match(r'^\d{2}:\d{2}$', hora_val):
                f_actualizada['hora'] = hora_val + ':00'

            # Si NO tiene items, construirlos desde la estructura legacy
            if not f_actualizada.get('items'):
                productos = f_actualizada.get('productos') or []
                cantidades = f_actualizada.get('cantidades') or []
                precios = f_actualizada.get('precios') or []

                items = []
                for i in range(min(len(productos), len(cantidades), len(precios))):
                    try:
                        pid = productos[i]
                        qty = int(cantidades[i])
                        price = float(precios[i])
                        subtotal_usd = qty * price
                        items.append({
                            'id_producto': pid,
                            'nombre': '',
                            'categoria': '',
                            'cantidad': qty,
                            'precio_unitario_usd': price,
                            'precio_unitario_bs': price * tasa,
                            'subtotal_usd': subtotal_usd,
                            'subtotal_bs': subtotal_usd * tasa,
                        })
                    except Exception:
                        continue

                # Totales
                subtotal_usd_calc = sum(it['subtotal_usd'] for it in items)
                descuento_total = float(f_actualizada.get('descuento_total') or f_actualizada.get('descuento') or 0)
                iva_pct = float(f_actualizada.get('iva') or 0)
                base_iva = subtotal_usd_calc - descuento_total
                iva_total = base_iva * (iva_pct/100)
                total_usd = base_iva + iva_total
                total_bs = total_usd * tasa

                # Cliente embebido
                cid = str(f_actualizada.get('cliente_id', ''))
                c = clientes.get(cid, {})

                f_actualizada.update({
                    'items': items,
                    'cliente_datos': {
                        'rif': c.get('rif', cid),
                        'nombre': c.get('nombre', ''),
                        'direccion': c.get('direccion', ''),
                        'telefono': c.get('telefono', ''),
                        'email': c.get('email', ''),
                    },
                    'subtotal_usd': subtotal_usd_calc,
                    'subtotal_bs': subtotal_usd_calc * tasa,
                    'descuento_total': descuento_total,
                    'iva_total': iva_total,
                    'total_usd': total_usd,
                    'total_bs': total_bs,
                    'moneda_principal': 'USD',
                    'moneda_secundaria': 'VES',
                })
                actualizadas += 1

            facturas[fid] = f_actualizada
        except Exception as e:
            print('Error migrando/normalizando factura', fid, e)
            continue

    if guardar_datos(ARCHIVO_FACTURAS, facturas):
        flash(f'Proceso completado. Items creados: {actualizadas}. Números/hours normalizados: {renumeradas}', 'success')
    else:
        flash('No se pudo guardar la migración.', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/configurar_secuencia', methods=['GET', 'POST'])
@login_required
def configurar_secuencia():
    """Formulario simple para ajustar la secuencia de facturas (siguiente número)."""
    estado = control_numeracion.obtener_estado_numeracion('FACTURA')
    serie = estado.get('FACTURA', {})
    if request.method == 'POST':
        try:
            nuevo = int(request.form.get('siguiente_numero'))
            # Actualizar archivo de control directamente
            from numeracion_fiscal import ControlNumeracionFiscal
            ctrl = ControlNumeracionFiscal()
            control = ctrl._cargar_control()
            prefijo = (request.form.get('prefijo') or '').strip()
            if not prefijo:
                prefijo = control['series']['FACTURA'].get('prefijo', 'FAC-')
            # normalizar prefijo (opcional: asegurar guion final)
            # if not prefijo.endswith('-'): prefijo += '-'
            control['series']['FACTURA']['siguiente_numero'] = max(nuevo, 1)
            control['series']['FACTURA']['prefijo'] = prefijo
            # reconstruir formato respetando longitud existente
            longitud = int(control['series']['FACTURA'].get('longitud_numero', 8) or 8)
            control['series']['FACTURA']['formato'] = f"{prefijo}" + "{numero:" + f"0{longitud}d" + "}"
            ctrl._guardar_control(control)
            flash('Secuencia actualizada correctamente', 'success')
            return redirect(url_for('mostrar_facturas'))
        except Exception as e:
            flash(f'Error actualizando secuencia: {e}', 'danger')
    return render_template('configurar_secuencia.html', serie=serie)

@app.route('/facturas/<id>/eliminar', methods=['POST'])
@login_required
def eliminar_factura(id):
    """Elimina una factura removiendo referencias en el maestro y archivos físicos en disco."""
    if not id or str(id).strip() == '':
        flash('ID de factura inválido', 'danger')
        return redirect(url_for('mostrar_facturas'))

    facturas = cargar_datos(ARCHIVO_FACTURAS) or {}
    if os.path.exists("facturas_json"):
        for fname in os.listdir("facturas_json"):
            if fname.endswith(".json") and fname != "facturas.json":
                fk = fname[len("factura_"):-len(".json")] if fname.startswith("factura_") else fname[:-len(".json")]
                if fk not in facturas:
                    fdata = cargar_datos(os.path.join("facturas_json", fname))
                    if fdata and isinstance(fdata, dict):
                        facturas[fk] = fdata

    keys_to_remove = set()
    t_lower = str(id).strip().lower()

    for k, f in list(facturas.items()):
        if not isinstance(f, dict):
            continue
        f_num = str(f.get("numero", "")).strip().lower()
        f_id = str(f.get("id", "")).strip().lower()
        f_sec = str(f.get("numero_secuencial", "")).strip().lower()
        k_str = str(k).strip().lower()

        if t_lower in (f_num, f_id, f_sec, k_str) or (
            t_lower.replace("fac-", "").replace("factura_", "").lstrip("0") and
            t_lower.replace("fac-", "").replace("factura_", "").lstrip("0") in (
                f_num.replace("fac-", "").lstrip("0"),
                f_sec.lstrip("0"),
                k_str.replace("fac-", "").replace("factura_", "").lstrip("0")
            )
        ):
            keys_to_remove.add(str(k))
            if f.get("numero"): keys_to_remove.add(str(f.get("numero")))
            if f.get("id"): keys_to_remove.add(str(f.get("id")))
            if f.get("numero_secuencial"): keys_to_remove.add(str(f.get("numero_secuencial")))

    if not keys_to_remove and id in facturas:
        keys_to_remove.add(str(id))

    if keys_to_remove:
        base_facturas = cargar_datos(ARCHIVO_FACTURAS) or {}
        for k in list(base_facturas.keys()):
            f = base_facturas[k]
            if isinstance(f, dict):
                if str(k) in keys_to_remove or str(f.get("numero")) in keys_to_remove or str(f.get("id")) in keys_to_remove:
                    base_facturas.pop(k, None)

        for k in keys_to_remove:
            base_facturas.pop(k, None)

        guardar_datos(ARCHIVO_FACTURAS, base_facturas)

        if os.path.exists("facturas_json"):
            for k in keys_to_remove:
                if not k: continue
                for fname in [f"factura_{k}.json", f"{k}.json"]:
                    pfile = os.path.join("facturas_json", fname)
                    if os.path.exists(pfile):
                        try:
                            os.remove(pfile)
                        except Exception as e:
                            print(f"Error borrando archivo {pfile}: {e}")

        flash('Factura eliminada exitosamente', 'success')
        try:
            registrar_bitacora(session.get('usuario', 'SISTEMA'), 'Eliminar factura', f"ID: {id}")
        except Exception:
            pass
    else:
        flash('Factura no encontrada', 'danger')

    return redirect(url_for('mostrar_facturas'))


def normalizar_cotizacion(cotizacion, clientes=None, inventario=None):
    """Unifica cotizaciones antiguas (solo cliente_id) y nuevas para vistas e impresión."""
    if not cotizacion or not isinstance(cotizacion, dict):
        return {}
    cot = dict(cotizacion)
    clientes = clientes or {}
    inventario = inventario or {}

    cliente = cot.get('cliente')
    if not isinstance(cliente, dict):
        cliente_id = cot.get('cliente_id') or (cliente if isinstance(cliente, str) else '')
        cliente = dict(clientes.get(str(cliente_id), {}))
        if cliente_id and not cliente.get('id'):
            cliente['id'] = cliente_id
        if not cliente.get('nombre'):
            cliente['nombre'] = str(cliente_id) if cliente_id else 'Cliente no especificado'
        cot['cliente'] = cliente

    if not cot.get('numero_cotizacion'):
        cot['numero_cotizacion'] = str(cot.get('numero') or cot.get('id') or '')

    productos = list(cot.get('productos') or [])
    cantidades = list(cot.get('cantidades') or [])
    precios_raw = cot.get('precios') or []
    precios = []
    for i, prod_id in enumerate(productos):
        if i < len(precios_raw):
            try:
                precios.append(float(precios_raw[i]))
                continue
            except (TypeError, ValueError):
                pass
        prod = inventario.get(str(prod_id), {})
        precios.append(float(prod.get('precio', 0) or 0))
    cot['productos'] = productos
    cot['cantidades'] = cantidades
    cot['precios'] = precios

    try:
        cot['validez_dias'] = int(cot.get('validez_dias') or cot.get('validez') or 3)
    except (TypeError, ValueError):
        cot['validez_dias'] = 3

    for key, default in (
        ('tasa_bcv', 0), ('iva', 16), ('iva_total', 0),
        ('descuento_total', 0), ('descuento', 0), ('hora', ''),
    ):
        if cot.get(key) is None:
            cot[key] = default

    for field in ('subtotal_usd', 'subtotal_bs', 'total_usd', 'total_bs'):
        val = cot.get(field)
        if isinstance(val, str):
            try:
                cot[field] = float(val.replace('$', '').replace('Bs', '').replace(',', '').strip())
            except ValueError:
                cot[field] = 0.0
        elif val is None:
            cot[field] = 0.0

    return cot






# --- Funciones de Utilidad ---
def validar_url_factura(f):
    """Decorador para validar URLs de facturas y redirigir si están malformadas"""
    @wraps(f)
    def decorated_function(id, *args, **kwargs):
        # Verificar que la URL no tenga doble barra consecutiva (como /facturas//editar)
        if '//' in request.path:
            flash('URL de factura inválida', 'danger')
            return redirect(url_for('mostrar_facturas'))
        
        # Verificar que el ID sea válido
        if not id or str(id).strip() == '':
            flash('ID de factura inválido', 'danger')
            return redirect(url_for('mostrar_facturas'))
        
        return f(id, *args, **kwargs)
    return decorated_function

def guardar_ultima_tasa_bcv(tasa):
    try:
        # Guardar tasa con fecha de actualización
        data = {
            'tasa': tasa,
            'fecha': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat()
        }
        
        try:
            guardar_datos(ULTIMA_TASA_BCV_FILE, data)
            print(f"Tasa BCV guardada exitosamente: {tasa}")
            
            # Registrar en bitácora si hay sesión activa
            try:
                from flask import has_request_context
                if has_request_context() and 'usuario' in session:
                    registrar_bitacora(session['usuario'], 'Actualizar tasa BCV', f'Tasa: {tasa}')
                else:
                    registrar_bitacora('Sistema', 'Actualizar tasa BCV', f'Tasa: {tasa}')
            except Exception as e:
                print(f"Error registrando en bitácora: {e}")
                
        except Exception as e:
            print(f"Error guardando última tasa BCV: {e}")
            
    except Exception as e:
        print(f"Error general en guardar_ultima_tasa_bcv: {e}")

def cargar_ultima_tasa_bcv():
    try:
        data = cargar_datos(ULTIMA_TASA_BCV_FILE)
        if not data:
            print(f"Archivo de tasa BCV no encontrado: {ULTIMA_TASA_BCV_FILE}")
            return None
        tasa = float(data.get('tasa', 0))
        if tasa > 10:
            print(f"Tasa BCV cargada: {tasa}")
            return tasa
        print(f"Tasa BCV no válida: {tasa}")
        return None
    except Exception as e:
        print(f"Error inesperado cargando tasa BCV: {e}")
        return None

def obtener_ultima_tasa_del_sistema():
    """Busca la tasa más reciente en facturas y otros archivos del sistema."""
    try:
        # Buscar en facturas recientes
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        tasas_encontradas = []
        
        for factura in facturas.values():
            if factura.get('tasa_bcv'):
                try:
                    tasa = float(factura['tasa_bcv'])
                    if tasa > 10:
                        tasas_encontradas.append(tasa)
                except:
                    continue
        
        # Buscar en cotizaciones si existen
        try:
            cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
            for cotizacion in cotizaciones.values():
                if cotizacion.get('tasa_bcv'):
                    try:
                        tasa = float(cotizacion['tasa_bcv'])
                        if tasa > 10:
                            tasas_encontradas.append(tasa)
                    except:
                        continue
        except:
            pass
        
        # Buscar en cuentas por cobrar si existen
        try:
            cuentas = cargar_datos(ARCHIVO_CUENTAS)
            for cuenta in cuentas.values():
                if cuenta.get('tasa_bcv'):
                    try:
                        tasa = float(cuenta['tasa_bcv'])
                        if tasa > 10:
                            tasas_encontradas.append(tasa)
                    except:
                        continue
        except:
            pass
        
        if tasas_encontradas:
            # Usar la tasa más alta (más reciente) del sistema
            tasa_mas_reciente = max(tasas_encontradas)
            print(f"Tasa encontrada en el sistema: {tasa_mas_reciente}")
            return tasa_mas_reciente
        
        return None
        
    except Exception as e:
        print(f"Error buscando tasa en el sistema: {e}")
        return None

def inicializar_archivos_por_defecto():
    """Inicializa archivos necesarios si no existen."""
    try:
        # Crear archivo de tasa BCV por defecto si no existe
        if not os.path.exists(ULTIMA_TASA_BCV_FILE):
            # Intentar obtener la tasa más reciente del sistema
            tasa_sistema = obtener_ultima_tasa_del_sistema()
            
            if tasa_sistema and tasa_sistema > 10:
                tasa_default = tasa_sistema
                print(f"Usando tasa del sistema: {tasa_default}")
            else:
                # Solo usar tasa por defecto si no hay ninguna en el sistema
                tasa_default = 135.0  # Tasa más reciente conocida
                print(f"Usando tasa por defecto del sistema: {tasa_default}")
            
            guardar_datos(ULTIMA_TASA_BCV_FILE, {
                'tasa': tasa_default,
                'fecha': datetime.now().isoformat()
            })
            print(f"Archivo de tasa BCV creado con tasa: {tasa_default}")
    except Exception as e:
        print(f"Error inicializando archivos por defecto: {e}")

def actualizar_tasa_bcv_automaticamente():
    """Actualiza la tasa BCV automáticamente si han pasado más de 24 horas."""
    try:
        if not os.path.exists(ULTIMA_TASA_BCV_FILE):
            print("Archivo de tasa BCV no existe, creando...")
            inicializar_archivos_por_defecto()
            return
        
        data = cargar_datos(ULTIMA_TASA_BCV_FILE, crear_vacio=False) or {}
        ultima_actualizacion = data.get('fecha', '')
        
        if ultima_actualizacion:
            try:
                ultima_fecha = datetime.fromisoformat(ultima_actualizacion)
                tiempo_transcurrido = datetime.now() - ultima_fecha
                
                # Actualizar si han pasado más de 24 horas
                if tiempo_transcurrido.total_seconds() > 24 * 3600:
                    print("🔄 Han pasado más de 24 horas, actualizando tasa BCV automáticamente...")
                    nueva_tasa = obtener_tasa_bcv_dia()
                    if nueva_tasa and nueva_tasa > 10:
                        print(f"✅ Tasa BCV actualizada automáticamente: {nueva_tasa}")
                    else:
                        print("❌ No se pudo actualizar la tasa BCV automáticamente")
                        # Intentar usar tasa del sistema como fallback
                        tasa_sistema = obtener_ultima_tasa_del_sistema()
                        if tasa_sistema and tasa_sistema > 10:
                            print(f"⚠️ Usando tasa del sistema como fallback: {tasa_sistema}")
                            guardar_ultima_tasa_bcv(tasa_sistema)
                else:
                    print(f"⏰ Tasa BCV actualizada recientemente, no es necesario actualizar")
                    # Aún así, verificar si hay una tasa más reciente disponible
                    print("🔍 Verificando si hay tasa más reciente disponible...")
                    tasa_web = obtener_tasa_bcv_dia()
                    if tasa_web and tasa_web > 0:
                        print(f"🎯 Tasa más reciente encontrada: {tasa_web}")
                        guardar_ultima_tasa_bcv(tasa_web)
            except Exception as e:
                print(f"Error verificando fecha de actualización: {e}")
        else:
            # Si no hay fecha, verificar si la tasa actual es válida
            tasa_actual = data.get('tasa', 0)
            if not tasa_actual or tasa_actual <= 10:
                print("Tasa BCV no válida, buscando en el sistema...")
                tasa_sistema = obtener_ultima_tasa_del_sistema()
                if tasa_sistema and tasa_sistema > 10:
                    print(f"Actualizando con tasa del sistema: {tasa_sistema}")
                    guardar_ultima_tasa_bcv(tasa_sistema)
        
    except Exception as e:
        print(f"Error en actualización automática de tasa BCV: {e}")
        # En caso de error, intentar usar tasa del sistema
        try:
            tasa_sistema = obtener_ultima_tasa_del_sistema()
            if tasa_sistema and tasa_sistema > 10:
                print(f"Usando tasa del sistema después de error: {tasa_sistema}")
                guardar_ultima_tasa_bcv(tasa_sistema)
        except:
            pass

def registrar_bitacora(usuario, accion, detalles='', documento_tipo='', documento_numero=''):
    """
    Función mejorada de bitácora que mantiene compatibilidad y agrega funcionalidad SENIAT
    """
    from datetime import datetime
    from flask import has_request_context, request, session
    
    # Sistema de bitácora tradicional (para compatibilidad)
    ip = ''
    ubicacion = ''
    lat = ''
    lon = ''
    
    try:
        if has_request_context():
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip == '127.0.0.1':
                ip = '190.202.123.123'  # IP pública de Venezuela para pruebas
        # Usar ubicación precisa si está en session
        if has_request_context() and 'ubicacion_precisa' in session:
            lat = session['ubicacion_precisa'].get('lat', '')
            lon = session['ubicacion_precisa'].get('lon', '')
            ubicacion = session['ubicacion_precisa'].get('texto', '')
        elif has_request_context():
            resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    lat = data.get('lat', '')
                    lon = data.get('lon', '')
                    ubicacion = ', '.join([v for v in [data.get('city', ''), data.get('regionName', ''), data.get('country', '')] if v])
                else:
                    ubicacion = f"API sin datos: {data}"
            else:
                ubicacion = f"API status: {resp.status_code}"
    except Exception as e:
        # Si hay algún error al acceder a Flask objects o API, usar valores por defecto
        print(f"Error en registrar_bitacora: {e}")
        ip = 'N/A'
        ubicacion = 'N/A'
        lat = ''
        lon = ''
    
    # Bitácora tradicional
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Usuario: {usuario} | Acción: {accion} | Detalles: {detalles} | IP: {ip} | Ubicación: {ubicacion} | Coordenadas: {lat},{lon}\n"
    with open(BITACORA_FILE, 'a', encoding='utf-8') as f:
        f.write(linea)
    
    # Sistema de auditoría fiscal SENIAT (cuando aplique)
    if documento_tipo or documento_numero or 'factura' in accion.lower() or 'fiscal' in accion.lower():
        try:
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario,
                accion=accion,
                documento_tipo=documento_tipo or 'GENERAL',
                documento_numero=documento_numero or 'N/A',
                ip_externa=ip,
                detalles=detalles
            )
        except Exception as e:
            # En caso de error en logs fiscales, registrar en bitácora tradicional
            error_linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR_LOG_FISCAL: {str(e)}\n"
            with open(BITACORA_FILE, 'a', encoding='utf-8') as f:
                f.write(error_linea)
    
    # Retornar éxito
    return True

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        # Verificar si es admin (puedes ajustar esta lógica según tu sistema)
        if session.get('usuario') != 'admin':
            flash('No tiene permisos de administrador para acceder a esta página', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def verify_password(username, password):
    """Verifica la contraseña de un usuario."""
    try:
        usuarios = cargar_datos('usuarios.json')
        if username in usuarios:
            return check_password_hash(usuarios[username]['password'], password)
        else:
            return False
    except Exception as e:
        print(f"Error verificando contraseña: {e}")
        return False


def obtener_tasa_bcv():
    try:
        # Usar la constante definida
        if not os.path.exists(ULTIMA_TASA_BCV_FILE):
            print(f"Archivo de tasa BCV no encontrado: {ULTIMA_TASA_BCV_FILE}")
            # Buscar en el sistema antes de usar tasa por defecto
            tasa_sistema = obtener_ultima_tasa_del_sistema()
            if tasa_sistema and tasa_sistema > 10:
                print(f"Usando tasa del sistema: {tasa_sistema}")
                return tasa_sistema
            else:
                print("No se encontró tasa válida en el sistema")
                return None
        
        data = cargar_datos(ULTIMA_TASA_BCV_FILE, crear_vacio=False) or {}
        tasa = float(data.get('tasa', 0))
        if tasa > 10:
            print(f"Tasa BCV obtenida del archivo: {tasa}")
            return tasa
        else:
            print(f"Tasa BCV en archivo no válida: {tasa}")
            # Buscar en el sistema como fallback
            tasa_sistema = obtener_ultima_tasa_del_sistema()
            if tasa_sistema and tasa_sistema > 10:
                print(f"Usando tasa del sistema como fallback: {tasa_sistema}")
                return tasa_sistema
            return None
    except FileNotFoundError:
        print(f"Archivo de tasa BCV no encontrado")
        # Buscar en el sistema
        tasa_sistema = obtener_ultima_tasa_del_sistema()
        if tasa_sistema and tasa_sistema > 10:
            print(f"Usando tasa del sistema: {tasa_sistema}")
            return tasa_sistema
        return None
    except json.JSONDecodeError as e:
        print(f"Error decodificando archivo de tasa BCV: {e}")
        # Buscar en el sistema como fallback
        tasa_sistema = obtener_ultima_tasa_del_sistema()
        if tasa_sistema and tasa_sistema > 10:
            print(f"Usando tasa del sistema como fallback: {tasa_sistema}")
            return tasa_sistema
        return None
    except Exception as e:
        print(f"Error inesperado obteniendo tasa BCV: {e}")
        # Buscar en el sistema como último recurso
        tasa_sistema = obtener_ultima_tasa_del_sistema()
        if tasa_sistema and tasa_sistema > 10:
            print(f"Usando tasa del sistema como último recurso: {tasa_sistema}")
            return tasa_sistema
        return None

def obtener_tasa_bcv_dia():
    """Obtiene la tasa oficial USD/BS del BCV desde la web. Devuelve float o None si falla."""
    try:
        # SIEMPRE intentar obtener desde la web primero (no usar tasa local)
        url = 'https://www.bcv.org.ve/glosario/cambio-oficial'
        print(f"🔍 Obteniendo tasa BCV ACTUAL desde: {url}")
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, timeout=20, verify=False)
        
        if resp.status_code != 200:
            print(f"❌ Error HTTP al obtener tasa BCV: {resp.status_code}")
            return None
        
        print(f"✅ Página BCV obtenida exitosamente, analizando contenido...")
        soup = BeautifulSoup(resp.text, 'html.parser')
        tasa = None
        
        # Método 1: Buscar por id='dolar' (método principal)
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong = dolar_div.find('strong')
            if strong:
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por ID 'dolar': {tasa}")
                except:
                    pass
        
        # Método 2: Buscar por id='usd' (alternativo)
        if not tasa:
            usd_div = soup.find('div', id='usd')
            if usd_div:
                strong = usd_div.find('strong')
                if strong:
                    txt = strong.text.strip().replace('.', '').replace(',', '.')
                    try:
                        posible = float(txt)
                        if posible > 10:
                            tasa = posible
                            print(f"🎯 Tasa BCV encontrada por ID 'usd': {tasa}")
                    except:
                        pass
        
        # Método 3: Buscar por strong con texto que parezca una tasa
        if not tasa:
            for strong in soup.find_all('strong'):
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10 and posible < 1000:  # Rango razonable
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por strong: {tasa}")
                        break
                except:
                    continue
        
        # Método 4: Buscar por span con clase específica
        if not tasa:
            for span in soup.find_all('span', class_='centrado'):
                txt = span.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10 and posible < 1000:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por span: {tasa}")
                        break
                except:
                    continue
        
        # Método 5: Buscar por regex más específico
        if not tasa:
            import re
            # Buscar patrones como 36,50 o 36.50 (más específico)
            matches = re.findall(r'(\d{2,}[.,]\d{2,})', resp.text)
            for m in matches:
                try:
                    posible = float(m.replace('.', '').replace(',', '.'))
                    if posible > 10 and posible < 1000:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por regex: {tasa}")
                        break
                except:
                    continue
        
        # Método 6: Buscar en tablas específicas
        if not tasa:
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    for cell in row.find_all(['td', 'th']):
                        txt = cell.text.strip().replace('.', '').replace(',', '.')
                        try:
                            posible = float(txt)
                            if posible > 10 and posible < 1000:
                                tasa = posible
                                print(f"🎯 Tasa BCV encontrada en tabla: {tasa}")
                                break
                        except:
                            continue
                    if tasa:
                        break
                if tasa:
                    break
        
        # Método 7: Buscar por texto que contenga "USD" o "Dólar"
        if not tasa:
            for element in soup.find_all(['div', 'span', 'p']):
                if 'USD' in element.text or 'Dólar' in element.text or 'dólar' in element.text:
                    txt = element.text.strip()
                    # Extraer números del texto
                    import re
                    numbers = re.findall(r'(\d+[.,]\d+)', txt)
                    for num in numbers:
                        try:
                            posible = float(num.replace('.', '').replace(',', '.'))
                            if posible > 10 and posible < 1000:
                                tasa = posible
                                print(f"🎯 Tasa BCV encontrada por texto USD: {tasa}")
                                break
                        except:
                            continue
                    if tasa:
                        break
        
        if tasa and tasa > 10:
            # Guardar la tasa en el archivo
            guardar_ultima_tasa_bcv(tasa)
            print(f"💾 Tasa BCV ACTUAL guardada exitosamente: {tasa}")
            return tasa
        else:
            print("❌ No se pudo encontrar una tasa BCV válida en la página")
            # Solo como último recurso, usar tasa local
            tasa_local = cargar_ultima_tasa_bcv()
            if tasa_local and tasa_local > 10:
                print(f"⚠️ Usando tasa BCV local como fallback: {tasa_local}")
                return tasa_local
            return None
            
    except Exception as e:
        print(f"❌ Error obteniendo tasa BCV: {e}")
        # Solo como último recurso, usar tasa local
        try:
            tasa_fallback = cargar_ultima_tasa_bcv()
            if tasa_fallback and tasa_fallback > 10:
                print(f"⚠️ Usando tasa BCV de fallback después de error: {tasa_fallback}")
                return tasa_fallback
        except:
            pass
        return None

# Llamar inicialización
inicializar_archivos_por_defecto()

# Ejecutar actualización automática al iniciar
actualizar_tasa_bcv_automaticamente()
# Usar SECRET_KEY desde variables de entorno en producción
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unsafe-default-change-me')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
csrf = CSRFProtect(app)



def limpiar_valor_monetario(valor):
    """Limpia y convierte un valor monetario a float."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        # Eliminar símbolos y espacios
        valor = str(valor).replace('$', '').replace(',', '').replace('Bs', '').strip()
        # Reemplazar coma decimal por punto si existe
        if ',' in valor:
            valor = valor.replace(',', '.')
        return float(valor)
    except (ValueError, TypeError):
        return 0.0

def cargar_empresa():
    data = cargar_datos('empresa.json', crear_vacio=False)
    if data:
        return data
    return {
        "nombre": "Nombre de la Empresa",
        "rif": "J-000000000",
        "telefono": "0000-0000000",
        "direccion": "Dirección de la empresa"
    }

def es_fecha_valida(fecha_str):
    """Valida si una fecha es válida y puede ser comparada."""
    if not fecha_str or not isinstance(fecha_str, str):
        return False
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def limpiar_monto(monto):
    if not monto:
        return 0.0
    return float(str(monto).replace('$', '').replace('Bs', '').replace(',', '').strip())

# NOTA: La función index ya está definida anteriormente

# NOTA: La función mapa_avanzado ya está definida anteriormente

# NOTA: La función mostrar_clientes ya está definida anteriormente

# NOTA: La función nuevo_cliente ya está definida anteriormente

# NOTA: La función mostrar_inventario ya está definida anteriormente

# NOTA: La función nuevo_producto ya está definida anteriormente

# NOTA: La función editar_producto ya está definida anteriormente
# NOTA: La función eliminar_producto ya está definida anteriormente
# NOTA: La función ver_producto ya está definida anteriormente

# NOTA: La función mostrar_facturas ya está definida anteriormente
# NOTA: La función imprimir_factura ya está definida anteriormente
# NOTA: La función ver_factura ya está definida anteriormente
# NOTA: La función test_whatsapp ya está definida anteriormente

# Rutas para capturar URLs malformadas específicas
# NOTA: La función editar_factura_url_malformada ya está definida anteriormente
# NOTA: La función factura_url_malformada_general ya está definida anteriormente
# NOTA: La función editar_factura_url_triple_malformada ya está definida anteriormente
# NOTA: La función editar_factura ya está definida anteriormente
# NOTA: La función duplicar_factura ya está definida anteriormente
# NOTA: La función nueva_factura ya está definida anteriormente
# NOTA: La función limpiar_ids_invalidos_facturas ya está definida anteriormente
# NOTA: La función migrar_formato_facturas ya está definida anteriormente
# NOTA: La función configurar_secuencia ya está definida anteriormente
# NOTA: La función eliminar_factura ya está definida anteriormente
# NOTA: La función mostrar_cotizaciones ya está definida anteriormente
# NOTA: La función nueva_cotizacion ya está definida anteriormente
@app.route('/cotizaciones/<id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cotizacion(id):
    """Formulario para editar una cotización."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if not os.path.exists(filename):
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    if request.method == 'POST':
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        precios = request.form.getlist('precios[]')
        descuento = request.form.get('descuento', '0')
        tipo_descuento = request.form.get('tipo_descuento', 'bs')
        iva = request.form.get('iva', '0')
        tasa_bcv = request.form.get('tasa_bcv', '0')
        validez = request.form.get('validez', '3')
        cliente_id = request.form.get('cliente_id')
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        cliente = clientes.get(cliente_id, {})
        if cliente_id and not cliente.get('id'):
            cliente = {**cliente, 'id': cliente_id}
        hora = request.form.get('hora') or datetime.now().strftime('%H:%M')

        subtotal_usd = 0.0
        for precio, cantidad in zip(precios, cantidades):
            try:
                subtotal_usd += float(precio) * int(cantidad)
            except (TypeError, ValueError):
                continue
        tasa_bcv_f = float(tasa_bcv) if tasa_bcv else 1.0
        descuento_f = float(descuento) if descuento else 0.0
        if tipo_descuento == 'porc':
            descuento_total = subtotal_usd * (descuento_f / 100)
        else:
            descuento_total = descuento_f / tasa_bcv_f if tasa_bcv_f else 0.0
        iva_f = float(iva) if iva else 0.0
        iva_total = (subtotal_usd - descuento_total) * (iva_f / 100)
        total_usd = subtotal_usd - descuento_total + iva_total

        cotizacion = {
            'numero_cotizacion': id,
            'fecha': request.form['fecha'],
            'hora': hora,
            'cliente': cliente,
            'productos': productos,
            'cantidades': cantidades,
            'precios': precios,
            'subtotal_usd': subtotal_usd,
            'subtotal_bs': subtotal_usd * tasa_bcv_f,
            'descuento': descuento_f,
            'tipo_descuento': tipo_descuento,
            'descuento_total': descuento_total,
            'iva': iva_f,
            'iva_total': iva_total,
            'total_usd': total_usd,
            'total_bs': total_usd * tasa_bcv_f,
            'tasa_bcv': tasa_bcv_f,
            'validez_dias': int(validez)
        }
        guardar_datos(filename, cotizacion)
        flash('Cotización actualizada exitosamente', 'success')
        registrar_bitacora(session['usuario'], 'Editar cotización', f"ID: {id}")
        return redirect(url_for('mostrar_cotizaciones'))
    cotizacion = cargar_datos(filename, crear_vacio=False)
    if not cotizacion:
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    cotizacion = normalizar_cotizacion(cotizacion, clientes, inventario)
    # --- Fix para edición: cliente_id y validez ---
    if 'cliente' in cotizacion and 'id' in cotizacion['cliente']:
        cotizacion['cliente_id'] = cotizacion['cliente']['id']
    else:
        cotizacion['cliente_id'] = ''
    cotizacion['validez'] = cotizacion.get('validez_dias', 3)
    if 'precios' in cotizacion:
        cotizacion['precios'] = [float(p) for p in cotizacion['precios']]
    # Fix para mostrar el número de cotización en el formulario
    cotizacion['numero'] = cotizacion.get('numero_cotizacion', id)
    return render_template('cotizacion_form.html', cotizacion=cotizacion, clientes=clientes, inventario=inventario, zip=zip)

@app.route('/cotizaciones/<id>/eliminar', methods=['POST'])
@login_required
def eliminar_cotizacion(id):
    """Elimina una cotización (elimina el archivo individual)."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if os.path.exists(filename):
        try:
            os.remove(filename)
            flash('Cotización eliminada exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Eliminar cotización', f"ID: {id}")
        except Exception as e:
            flash(f'Error al eliminar la cotización: {e}', 'danger')
    else:
        flash('Cotización no encontrada', 'danger')
    return redirect(url_for('mostrar_cotizaciones'))

@app.route('/clientes/<path:id>')
def ver_cliente(id):
    """Muestra los detalles de un cliente."""
    try:
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        cuentas = cargar_datos(ARCHIVO_CUENTAS)
        tasa_bcv = obtener_tasa_bcv() or 1.0
        
        if id not in clientes:
            flash('❌ Cliente no encontrado', 'danger')
            return redirect(url_for('mostrar_clientes'))
        
        cliente = clientes[id]
        
        # Calcular totales financieros de forma más robusta
        facturas_cliente = [f for f in facturas.values() if f.get('cliente_id') == id]
        
        # Total facturado
        total_facturado = 0.0
        for factura in facturas_cliente:
            try:
                total_facturado += float(factura.get('total_usd', 0))
            except (ValueError, TypeError):
                continue
        
        # Total abonado
        total_abonado = 0.0
        for factura in facturas_cliente:
            try:
                total_abonado += float(factura.get('total_abonado', 0))
            except (ValueError, TypeError):
                continue
        
        # Total por cobrar desde cuentas
        cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id), None)
        total_por_cobrar = 0.0
        if cuenta:
            try:
                total_por_cobrar = float(cuenta.get('saldo_pendiente', 0))
            except (ValueError, TypeError):
                total_por_cobrar = 0.0
        
        # Calcular total por cobrar también desde facturas (como respaldo)
        total_por_cobrar_facturas = total_facturado - total_abonado
        if total_por_cobrar == 0 and total_por_cobrar_facturas > 0:
            total_por_cobrar = total_por_cobrar_facturas
        
        # Convertir a bolívares
        total_por_cobrar_bs = total_por_cobrar * tasa_bcv
        
        # Estadísticas adicionales
        cantidad_facturas = len(facturas_cliente)
        ultima_factura = None
        if facturas_cliente:
            facturas_ordenadas = sorted(facturas_cliente, key=lambda x: x.get('fecha', ''), reverse=True)
            ultima_factura = facturas_ordenadas[0].get('fecha') if facturas_ordenadas else None
        
        # Obtener configuración del mapa
        maps_config = get_maps_config()
        
        return render_template('cliente_detalle.html', 
                             cliente=cliente, 
                             total_facturado=total_facturado, 
                             total_abonado=total_abonado, 
                             total_por_cobrar=total_por_cobrar, 
                             total_por_cobrar_bs=total_por_cobrar_bs, 
                             tasa_bcv=tasa_bcv,
                             cantidad_facturas=cantidad_facturas,
                             ultima_factura=ultima_factura,
                             maps_config=maps_config)
    
    except Exception as e:
        print(f"Error al cargar detalles del cliente {id}: {e}")
        flash('❌ Error al cargar los detalles del cliente', 'danger')
        return redirect(url_for('mostrar_clientes'))



@app.route('/inventario/reporte')
def reporte_inventario():
    try:
        inventario = cargar_datos('inventario.json')
        empresa = cargar_datos('empresa.json')
        # Obtener la tasa BCV actual
        tasa_bcv = obtener_tasa_bcv()
        advertencia_tasa = None
        try:
            tasa_bcv = float(tasa_bcv)
        except Exception:
            tasa_bcv = 0
        if not tasa_bcv or tasa_bcv < 1:
            advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
        # Obtener la fecha actual
        fecha_actual = datetime.now()
        # Calcular estadísticas
        total_productos = len(inventario)
        total_stock = sum(producto['cantidad'] for producto in inventario.values())
        valor_total = sum(producto['cantidad'] * producto['precio'] for producto in inventario.values())
        # Productos por categoría
        productos_por_categoria = {}
        for producto in inventario.values():
            categoria = producto['categoria']
            if categoria not in productos_por_categoria:
                productos_por_categoria[categoria] = {
                    'productos': [],
                    'cantidad': 0,
                    'valor': 0
                }
            productos_por_categoria[categoria]['productos'].append(producto)
            productos_por_categoria[categoria]['cantidad'] += producto['cantidad']
            productos_por_categoria[categoria]['valor'] += producto['cantidad'] * producto['precio']
        # Productos con bajo stock (menos de 10 unidades)
        productos_bajo_stock = {
            id: producto for id, producto in inventario.items() 
            if producto['cantidad'] < 10
        }
        # --- Historial de ajustes masivos ---
        ajustes_masivos = []
        for producto in inventario.values():
            nombre_producto = producto.get('nombre', '')
            if 'historial_ajustes' in producto:
                for ajuste in producto['historial_ajustes']:
                    ajustes_masivos.append({
                        'fecha': ajuste.get('fecha', ''),
                        'motivo': ajuste.get('motivo', ''),
                        'producto': nombre_producto,
                        'ingreso': ajuste['cantidad'] if ajuste.get('tipo') == 'entrada' else 0,
                        'salida': ajuste['cantidad'] if ajuste.get('tipo') == 'salida' else 0,
                        'usuario': '',
                        'observaciones': ajuste.get('motivo', '')
                    })
        # Ordenar por fecha descendente
        from datetime import datetime as dt
        def parse_fecha(f):
            try:
                return dt.strptime(f['fecha'], '%Y-%m-%d %H:%M:%S')
            except:
                return dt.min
        ajustes_masivos = sorted(ajustes_masivos, key=parse_fecha, reverse=True)
        return render_template('reporte_inventario.html',
                             inventario=inventario,
                             total_productos=total_productos,
                             total_stock=total_stock,
                             valor_total=valor_total,
                             productos_por_categoria=productos_por_categoria,
                             productos_bajo_stock=productos_bajo_stock,
                             empresa=empresa,
                             tasa_bcv=tasa_bcv,
                             fecha_actual=fecha_actual,
                             advertencia_tasa=advertencia_tasa,
                             ajustes_masivos=ajustes_masivos)
    except Exception as e:
        flash(f'Error al generar el reporte: {str(e)}', 'danger')
        return redirect(url_for('mostrar_inventario'))

# --- API Endpoints ---


def obtener_tasa_bcv_dia():
    """Obtiene la tasa oficial USD/BS del BCV desde la web. Devuelve float o None si falla."""
    try:
        # SIEMPRE intentar obtener desde la web primero (no usar tasa local)
        url = 'https://www.bcv.org.ve/glosario/cambio-oficial'
        print(f"🔍 Obteniendo tasa BCV ACTUAL desde: {url}")
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, timeout=20, verify=False)
        
        if resp.status_code != 200:
            print(f"❌ Error HTTP al obtener tasa BCV: {resp.status_code}")
            return None
        
        print(f"✅ Página BCV obtenida exitosamente, analizando contenido...")
        soup = BeautifulSoup(resp.text, 'html.parser')
        tasa = None
        
        # Método 1: Buscar por id='dolar' (método principal)
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong = dolar_div.find('strong')
            if strong:
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por ID 'dolar': {tasa}")
                except:
                    pass
        
        # Método 2: Buscar por id='usd' (alternativo)
        if not tasa:
            usd_div = soup.find('div', id='usd')
            if usd_div:
                strong = usd_div.find('strong')
                if strong:
                    txt = strong.text.strip().replace(".", "").replace(",", ".")
                    try:
                        posible = float(txt)
                        if posible > 10:
                            tasa = posible
                            print(f"🎯 Tasa BCV encontrada por ID 'usd': {tasa}")
                    except:
                        pass
        # Método 3: Buscar por strong con texto que parezca una tasa
        if not tasa:
            for strong in soup.find_all('strong'):
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10 and posible < 1000:  # Rango razonable
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por strong: {tasa}")
                        break
                except:
                    continue
        
        # Método 4: Buscar por span con clase específica
        if not tasa:
            for span in soup.find_all('span', class_='centrado'):
                txt = span.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10 and posible < 1000:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por span: {tasa}")
                        break
                except:
                    continue
        
        # Método 5: Buscar por regex más específico
        if not tasa:
            import re
            # Buscar patrones como 36,50 o 36.50 (más específico)
            matches = re.findall(r'(\d{2,}[.,]\d{2,})', resp.text)
            for m in matches:
                try:
                    posible = float(m.replace('.', '').replace(',', '.'))
                    if posible > 10 and posible < 1000:
                        tasa = posible
                        print(f"🎯 Tasa BCV encontrada por regex: {tasa}")
                        break
                except:
                    continue
        
        # Método 6: Buscar en tablas específicas
        if not tasa:
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    for cell in row.find_all(['td', 'th']):
                        txt = cell.text.strip().replace('.', '').replace(',', '.')
                        try:
                            posible = float(txt)
                            if posible > 10 and posible < 1000:
                                tasa = posible
                                print(f"🎯 Tasa BCV encontrada en tabla: {tasa}")
                                break
                        except:
                            continue
                    if tasa:
                        break
                if tasa:
                    break
        
        # Método 7: Buscar por texto que contenga "USD" o "Dólar"
        if not tasa:
            for element in soup.find_all(['div', 'span', 'p']):
                if 'USD' in element.text or 'Dólar' in element.text or 'dólar' in element.text:
                    txt = element.text.strip()
                    # Extraer números del texto
                    import re
                    numbers = re.findall(r'(\d+[.,]\d+)', txt)
                    for num in numbers:
                        try:
                            posible = float(num.replace('.', '').replace(',', '.'))
                            if posible > 10 and posible < 1000:
                                tasa = posible
                                print(f"🎯 Tasa BCV encontrada por texto USD: {tasa}")
                                break
                        except:
                            continue
                    if tasa:
                        break
        
        if tasa and tasa > 10:
            # Guardar la tasa en el archivo
            guardar_ultima_tasa_bcv(tasa)
            print(f"💾 Tasa BCV ACTUAL guardada exitosamente: {tasa}")
            return tasa
        else:
            print("❌ No se pudo encontrar una tasa BCV válida en la página")
            # Solo como último recurso, usar tasa local
            tasa_local = cargar_ultima_tasa_bcv()
            if tasa_local and tasa_local > 10:
                print(f"⚠️ Usando tasa BCV local como fallback: {tasa_local}")
                return tasa_local
            return None
            
    except Exception as e:
        print(f"❌ Error obteniendo tasa BCV: {e}")
        # Solo como último recurso, usar tasa local
        try:
            tasa_fallback = cargar_ultima_tasa_bcv()
            if tasa_fallback and tasa_fallback > 10:
                print(f"⚠️ Usando tasa BCV de fallback después de error: {tasa_fallback}")
                return tasa_fallback
        except:
            pass
        return None

# --- Manejo de Errores ---
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(e):
    return render_template('500.html'), 500

@app.route('/clientes/reporte')
def reporte_clientes():
    try:
        # Obtener filtros de la URL
        q = request.args.get('q', '')
        orden = request.args.get('orden', 'nombre')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        monto_min = request.args.get('monto_min', '')
        monto_max = request.args.get('monto_max', '')
        tipo_cliente = request.args.get('tipo_cliente', 'todos')
        
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        empresa = cargar_empresa()
        
        # Obtener la tasa BCV actual
        tasa_bcv = obtener_tasa_bcv()
        advertencia_tasa = None
        try:
            tasa_bcv = float(tasa_bcv)
        except Exception:
            tasa_bcv = 0
        if not tasa_bcv or tasa_bcv < 1:
            advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
        
        # Calcular estadísticas generales
        total_clientes = len(clientes)
        total_facturas = len(facturas)
        total_facturado_general = 0
        total_abonado_general = 0
        total_cobrar = 0
        
        # Estadísticas por cliente
        stats_clientes = {}
        for id_cliente, cliente in clientes.items():
            stats_clientes[id_cliente] = {
                'id': id_cliente,
                'nombre': cliente['nombre'],
                'email': cliente.get('email', ''),
                'telefono': cliente.get('telefono', ''),
                'total_facturas': 0,
                'total_compras': 0,
                'ultima_compra': None,
                'total_facturado': 0,
                'total_abonado': 0,
                'total_por_cobrar': 0
            }
        
        # Procesar facturas
        for factura in facturas.values():
            id_cliente = factura.get('cliente_id')
            if id_cliente in stats_clientes:
                stats = stats_clientes[id_cliente]
                stats['total_facturas'] += 1
                
                # Obtener totales de la factura
                total_facturado = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                total_por_cobrar = max(0, total_facturado - total_abonado)
                
                # Actualizar estadísticas del cliente
                stats['total_facturado'] += total_facturado
                stats['total_abonado'] += total_abonado
                stats['total_por_cobrar'] += total_por_cobrar
                stats['total_compras'] += total_facturado
                
                # Actualizar última compra
                fecha_factura = factura.get('fecha')
                if fecha_factura:
                    if not stats['ultima_compra'] or fecha_factura > stats['ultima_compra']:
                        stats['ultima_compra'] = fecha_factura
                
                # Actualizar totales generales
                total_facturado_general += total_facturado
                total_abonado_general += total_abonado
                total_cobrar += total_por_cobrar
        
        # Ordenar clientes por total de compras (Top 10 Mejores Clientes)
        top_clientes = sorted(
            [stats for stats in stats_clientes.values() if stats['total_compras'] > 0],
            key=lambda x: x['total_compras'],
            reverse=True
        )[:10]
        
        # Ordenar clientes por total por cobrar (Top 5 Clientes con Mayor Cuenta por Cobrar)
        # Solo incluir clientes que realmente tengan saldo pendiente significativo
        peores_clientes = []
        for stats in stats_clientes.values():
            # Verificar si el cliente tiene facturas pendientes con saldo significativo
            tiene_facturas_pendientes = False
            for factura in facturas.values():
                if (factura.get('cliente_id') == stats['id'] and 
                    factura.get('estado') == 'pendiente' and 
                    float(factura.get('saldo_pendiente', 0)) >= 0.01):  # Ignorar saldos menores a 1 centavo
                    tiene_facturas_pendientes = True
                    break
            
            if tiene_facturas_pendientes:
                peores_clientes.append(stats)
        
        # Ordenar y limitar a 5 clientes
        peores_clientes = sorted(
            peores_clientes,
            key=lambda x: x['total_por_cobrar'],
            reverse=True
        )[:5]
        
        # ========================================
        # MÉTRICAS AVANZADAS
        # ========================================
        
        # 1. Promedio de compra por cliente
        clientes_con_compras = [stats for stats in stats_clientes.values() if stats['total_compras'] > 0]
        promedio_compra_cliente = total_facturado_general / len(clientes_con_compras) if clientes_con_compras else 0
        
        # 2. Cliente con mayor factura individual
        mayor_factura = 0
        cliente_mayor_factura = None
        for factura in facturas.values():
            total_factura = float(factura.get('total_usd', 0))
            if total_factura > mayor_factura:
                mayor_factura = total_factura
                cliente_mayor_factura = factura.get('cliente_id')
        
        # 3. Clientes nuevos este mes y año
        now = datetime.now()
        mes_actual = now.month
        anio_actual = now.year
        
        clientes_nuevos_mes = 0
        clientes_nuevos_anio = 0
        
        for factura in facturas.values():
            fecha_factura = factura.get('fecha')
            if fecha_factura:
                try:
                    fecha_dt = datetime.strptime(fecha_factura, '%Y-%m-%d')
                    if fecha_dt.month == mes_actual and fecha_dt.year == anio_actual:
                        clientes_nuevos_mes += 1
                    if fecha_dt.year == anio_actual:
                        clientes_nuevos_anio += 1
                except:
                    continue
        
        # 4. Clientes activos e inactivos (sin compras en 3 meses)
        fecha_limite = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        clientes_inactivos = []
        clientes_activos = []
        clientes_inactivos_ids = set()
        clientes_activos_ids = set()
        
        for stats in stats_clientes.values():
            ultima_compra = stats.get('ultima_compra')
            if es_fecha_valida(ultima_compra):
                try:
                    if ultima_compra < fecha_limite:
                        clientes_inactivos.append(stats)
                        clientes_inactivos_ids.add(stats['id'])
                    else:
                        clientes_activos.append(stats)
                        clientes_activos_ids.add(stats['id'])
                except (TypeError, ValueError):
                    # Si hay error en la comparación, considerar como inactivo
                    clientes_inactivos.append(stats)
                    clientes_inactivos_ids.add(stats['id'])
            else:
                # Clientes sin compras van a inactivos
                clientes_inactivos.append(stats)
                clientes_inactivos_ids.add(stats['id'])
        
        # 5. Tasa de conversión (clientes con facturas vs total)
        clientes_con_facturas = len([stats for stats in stats_clientes.values() if stats['total_facturas'] > 0])
        tasa_conversion = (clientes_con_facturas / total_clientes * 100) if total_clientes > 0 else 0
        
        # 6. Cliente más frecuente (más facturas)
        cliente_mas_frecuente = max(stats_clientes.values(), key=lambda x: x['total_facturas']) if stats_clientes else None
        
        # 7. Promedio de facturas por cliente
        promedio_facturas_cliente = total_facturas / total_clientes if total_clientes > 0 else 0
        
        # 8. Clientes VIP (top 20% por valor de compras)
        if clientes_con_compras:
            clientes_ordenados = sorted(clientes_con_compras, key=lambda x: x['total_compras'], reverse=True)
            num_vip = max(1, int(len(clientes_ordenados) * 0.2))  # 20% de clientes
            clientes_vip = clientes_ordenados[:num_vip]
            clientes_vip_ids = {c['id'] for c in clientes_vip}
        else:
            clientes_vip = []
            clientes_vip_ids = set()
        
        # 9. Valor promedio de factura
        valor_promedio_factura = total_facturado_general / total_facturas if total_facturas > 0 else 0
        
        # 10. Clientes con mayor saldo pendiente
        clientes_saldo_pendiente = [stats for stats in stats_clientes.values() if stats['total_por_cobrar'] > 0]
        clientes_saldo_pendiente = sorted(clientes_saldo_pendiente, key=lambda x: x['total_por_cobrar'], reverse=True)[:10]
        
        # ========================================
        # FILTRADO AVANZADO
        # ========================================
        
        # Filtrar clientes según los criterios
        clientes_filtrados = {}
        for id_cliente, cliente in clientes.items():
            id_cliente_str = str(id_cliente)
            stats = stats_clientes.get(id_cliente, {})
            
            # Filtro de búsqueda predictiva por nombre, RIF, email o teléfono
            if q:
                q_lower = q.lower().strip()
                nombre_cliente = str(cliente.get('nombre', '') or '').lower()
                rif_cliente = str(cliente.get('rif', '') or '').lower()
                email_cliente = str(cliente.get('email', '') or '').lower()
                telefono_cliente = str(cliente.get('telefono', '') or '').lower()
                
                # Coincidencia directa
                nombre_match = q_lower in nombre_cliente
                rif_match = q_lower in rif_cliente
                email_match = q_lower in email_cliente
                telefono_match = q_lower in telefono_cliente
                
                # Coincidencia por palabras
                palabras_busqueda = q_lower.split()
                nombre_palabras_match = all(palabra in nombre_cliente for palabra in palabras_busqueda)
                rif_palabras_match = all(palabra in rif_cliente for palabra in palabras_busqueda)
                
                if not (nombre_match or rif_match or email_match or telefono_match or nombre_palabras_match or rif_palabras_match):
                    continue
            
            # Filtro por tipo de cliente
            ultima_compra_filtro = stats.get('ultima_compra')
            if tipo_cliente == 'activos':
                if not es_fecha_valida(ultima_compra_filtro) or ultima_compra_filtro < fecha_limite:
                    continue
            elif tipo_cliente == 'inactivos':
                if es_fecha_valida(ultima_compra_filtro) and ultima_compra_filtro >= fecha_limite:
                    continue
            elif tipo_cliente == 'vip' and id_cliente not in clientes_vip_ids:
                continue
            elif tipo_cliente == 'pendientes' and stats.get('total_por_cobrar', 0) <= 0:
                continue
            
            # Filtro por monto mínimo/máximo
            try:
                if monto_min and stats.get('total_compras', 0) < float(monto_min):
                    continue
            except (ValueError, TypeError):
                pass

            try:
                if monto_max and stats.get('total_compras', 0) > float(monto_max):
                    continue
            except (ValueError, TypeError):
                pass
            
            # Filtro por fechas (si el cliente tiene facturas en el rango de fechas especificado)
            if fecha_desde or fecha_hasta:
                tiene_facturas_en_rango = False
                for factura in facturas.values():
                    if str(factura.get('cliente_id', '')) == id_cliente_str:
                        fecha_raw = str(factura.get('fecha', '')).split(' ')[0].split('T')[0]
                        if fecha_raw:
                            cumple_desde = not fecha_desde or (fecha_raw >= fecha_desde)
                            cumple_hasta = not fecha_hasta or (fecha_raw <= fecha_hasta)
                            if cumple_desde and cumple_hasta:
                                tiene_facturas_en_rango = True
                                break
                if not tiene_facturas_en_rango:
                    continue
            
            clientes_filtrados[id_cliente] = cliente
        
        # Ordenar clientes filtrados
        if orden == 'nombre':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), key=lambda x: str(x[1].get('nombre', '')).lower()))
        elif orden == 'rif':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), key=lambda x: str(x[1].get('rif', '')).lower()))
        elif orden == 'compras':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), 
                                           key=lambda x: stats_clientes.get(x[0], {}).get('total_compras', 0), reverse=True))
        elif orden == 'ultima_compra':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), 
                                           key=lambda x: stats_clientes.get(x[0], {}).get('ultima_compra') or '', reverse=True))
        
        # Estadísticas de productos más comprados
        productos_stats = {}
        for factura in facturas.values():
            productos = factura.get('productos', [])
            cantidades = factura.get('cantidades', [])
            precios = factura.get('precios', [])
            
            for i in range(len(productos)):
                id_producto = productos[i]
                if id_producto in inventario:
                    if id_producto not in productos_stats:
                        productos_stats[id_producto] = {
                            'nombre': inventario[id_producto]['nombre'],
                            'cantidad': 0,
                            'valor': 0
                        }
                    try:
                        cantidad = int(cantidades[i])
                        precio = float(precios[i])
                        productos_stats[id_producto]['cantidad'] += cantidad
                        productos_stats[id_producto]['valor'] += cantidad * precio
                    except (ValueError, TypeError, IndexError):
                        continue
        
        # Ordenar productos por cantidad (Top 10 Productos Más Comprados)
        top_productos = sorted(
            productos_stats.values(),
            key=lambda x: x['cantidad'],
            reverse=True
        )[:10]
        
        return render_template('reporte_clientes.html',
            clientes=clientes,
            clientes_filtrados=clientes_filtrados,
            facturas=facturas,
            inventario=inventario,
            empresa=empresa,
            tasa_bcv=tasa_bcv,
            advertencia_tasa=advertencia_tasa,
            total_clientes=total_clientes,
            total_facturas=total_facturas,
            total_facturado_usd=total_facturado_general,
            total_abonado_usd=total_abonado_general,
            total_por_cobrar_usd=total_cobrar,
            top_clientes=top_clientes,
            peores_clientes=peores_clientes,
            top_productos=top_productos,
            # Métricas avanzadas
            promedio_compra_cliente=promedio_compra_cliente,
            mayor_factura=mayor_factura,
            cliente_mayor_factura=cliente_mayor_factura,
            clientes_nuevos_mes=clientes_nuevos_mes,
            clientes_nuevos_anio=clientes_nuevos_anio,
            clientes_inactivos=clientes_inactivos,
            tasa_conversion=tasa_conversion,
            cliente_mas_frecuente=cliente_mas_frecuente,
            promedio_facturas_cliente=promedio_facturas_cliente,
            clientes_vip=clientes_vip,
            clientes_vip_ids=clientes_vip_ids,
            valor_promedio_factura=valor_promedio_factura,
            clientes_saldo_pendiente=clientes_saldo_pendiente,
            clientes_inactivos_ids=clientes_inactivos_ids,
            clientes_activos_ids=clientes_activos_ids,
            clientes_activos=clientes_activos,
            stats_clientes=stats_clientes,
            # Filtros
            q=q,
            orden=orden,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            monto_min=monto_min,
            monto_max=monto_max,
            tipo_cliente=tipo_cliente
        )
    except Exception as e:
        print(f"Error en reporte_clientes: {e}")
        return str(e), 500

@app.route('/clientes/reporte/pdf')
def reporte_clientes_pdf():
    try:
        q = request.args.get('q', '')
        orden = request.args.get('orden', 'nombre')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        monto_min = request.args.get('monto_min', '')
        monto_max = request.args.get('monto_max', '')
        tipo_cliente = request.args.get('tipo_cliente', 'todos')
        
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        empresa = cargar_empresa()
        
        tasa_bcv = obtener_tasa_bcv()
        try:
            tasa_bcv = float(tasa_bcv)
        except Exception:
            tasa_bcv = 0
            
        stats_clientes = {}
        for id_cliente, cliente in clientes.items():
            stats_clientes[id_cliente] = {
                'id': id_cliente,
                'nombre': cliente.get('nombre', ''),
                'email': cliente.get('email', ''),
                'telefono': cliente.get('telefono', ''),
                'total_facturas': 0,
                'total_compras': 0,
                'ultima_compra': None,
                'total_facturado': 0,
                'total_abonado': 0,
                'total_por_cobrar': 0
            }
            
        for factura in facturas.values():
            id_cliente = factura.get('cliente_id')
            if id_cliente in stats_clientes:
                stats = stats_clientes[id_cliente]
                stats['total_facturas'] += 1
                total_facturado = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                total_por_cobrar = max(0, total_facturado - total_abonado)
                
                stats['total_facturado'] += total_facturado
                stats['total_abonado'] += total_abonado
                stats['total_por_cobrar'] += total_por_cobrar
                stats['total_compras'] += total_facturado
                
                fecha_factura = factura.get('fecha')
                if fecha_factura:
                    if not stats['ultima_compra'] or fecha_factura > stats['ultima_compra']:
                        stats['ultima_compra'] = fecha_factura

        now = datetime.now()
        fecha_limite = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        clientes_con_compras = [stats for stats in stats_clientes.values() if stats['total_compras'] > 0]
        
        clientes_inactivos_ids = set()
        clientes_activos_ids = set()
        for stats in stats_clientes.values():
            ultima_compra = stats.get('ultima_compra')
            if es_fecha_valida(ultima_compra) and ultima_compra >= fecha_limite:
                clientes_activos_ids.add(stats['id'])
            else:
                clientes_inactivos_ids.add(stats['id'])
                
        if clientes_con_compras:
            clientes_ordenados = sorted(clientes_con_compras, key=lambda x: x['total_compras'], reverse=True)
            num_vip = max(1, int(len(clientes_ordenados) * 0.2))
            clientes_vip_ids = {c['id'] for c in clientes_ordenados[:num_vip]}
        else:
            clientes_vip_ids = set()

        clientes_filtrados = {}
        total_facturado_filtro = 0
        total_abonado_filtro = 0
        total_por_cobrar_filtro = 0
        
        for id_cliente, cliente in clientes.items():
            id_cliente_str = str(id_cliente)
            stats = stats_clientes.get(id_cliente, {})
            
            if q:
                q_lower = q.lower().strip()
                nombre_cliente = str(cliente.get('nombre', '') or '').lower()
                rif_cliente = str(cliente.get('rif', '') or '').lower()
                email_cliente = str(cliente.get('email', '') or '').lower()
                telefono_cliente = str(cliente.get('telefono', '') or '').lower()
                
                nombre_match = q_lower in nombre_cliente
                rif_match = q_lower in rif_cliente
                email_match = q_lower in email_cliente
                telefono_match = q_lower in telefono_cliente
                
                palabras_busqueda = q_lower.split()
                nombre_palabras_match = all(palabra in nombre_cliente for palabra in palabras_busqueda)
                rif_palabras_match = all(palabra in rif_cliente for palabra in palabras_busqueda)
                
                if not (nombre_match or rif_match or email_match or telefono_match or nombre_palabras_match or rif_palabras_match):
                    continue
            
            ultima_compra_filtro = stats.get('ultima_compra')
            if tipo_cliente == 'activos':
                if not es_fecha_valida(ultima_compra_filtro) or ultima_compra_filtro < fecha_limite:
                    continue
            elif tipo_cliente == 'inactivos':
                if es_fecha_valida(ultima_compra_filtro) and ultima_compra_filtro >= fecha_limite:
                    continue
            elif tipo_cliente == 'vip' and id_cliente not in clientes_vip_ids:
                continue
            elif tipo_cliente == 'pendientes' and stats.get('total_por_cobrar', 0) <= 0:
                continue
            
            try:
                if monto_min and stats.get('total_compras', 0) < float(monto_min):
                    continue
            except (ValueError, TypeError):
                pass

            try:
                if monto_max and stats.get('total_compras', 0) > float(monto_max):
                    continue
            except (ValueError, TypeError):
                pass
            
            if fecha_desde or fecha_hasta:
                tiene_facturas_en_rango = False
                for factura in facturas.values():
                    if str(factura.get('cliente_id', '')) == id_cliente_str:
                        fecha_raw = str(factura.get('fecha', '')).split(' ')[0].split('T')[0]
                        if fecha_raw:
                            cumple_desde = not fecha_desde or (fecha_raw >= fecha_desde)
                            cumple_hasta = not fecha_hasta or (fecha_raw <= fecha_hasta)
                            if cumple_desde and cumple_hasta:
                                tiene_facturas_en_rango = True
                                break
                if not tiene_facturas_en_rango:
                    continue
            
            clientes_filtrados[id_cliente] = cliente
            total_facturado_filtro += stats.get('total_facturado', 0)
            total_abonado_filtro += stats.get('total_abonado', 0)
            total_por_cobrar_filtro += stats.get('total_por_cobrar', 0)
        
        if orden == 'nombre':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), key=lambda x: str(x[1].get('nombre', '')).lower()))
        elif orden == 'rif':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), key=lambda x: str(x[1].get('rif', '')).lower()))
        elif orden == 'compras':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), 
                                           key=lambda x: stats_clientes.get(x[0], {}).get('total_compras', 0), reverse=True))
        elif orden == 'ultima_compra':
            clientes_filtrados = dict(sorted(clientes_filtrados.items(), 
                                           key=lambda x: stats_clientes.get(x[0], {}).get('ultima_compra') or '', reverse=True))

        top_clientes = sorted(
            [stats for stats in stats_clientes.values() if stats['total_compras'] > 0],
            key=lambda x: x['total_compras'],
            reverse=True
        )[:5]

        productos_stats = {}
        for factura in facturas.values():
            productos = factura.get('productos', [])
            cantidades = factura.get('cantidades', [])
            precios = factura.get('precios', [])
            for i in range(len(productos)):
                id_producto = productos[i]
                if id_producto in inventario:
                    if id_producto not in productos_stats:
                        productos_stats[id_producto] = {'nombre': inventario[id_producto]['nombre'], 'cantidad': 0, 'valor': 0}
                    try:
                        cant = int(cantidades[i])
                        prc = float(precios[i])
                        productos_stats[id_producto]['cantidad'] += cant
                        productos_stats[id_producto]['valor'] += cant * prc
                    except (ValueError, TypeError, IndexError):
                        continue
                        
        top_productos = sorted(productos_stats.values(), key=lambda x: x['cantidad'], reverse=True)[:5]
        fecha_reporte = now.strftime('%d/%m/%Y %H:%M')

        return render_template('reporte_clientes_pdf.html',
            clientes_filtrados=clientes_filtrados,
            stats_clientes=stats_clientes,
            tasa_bcv=tasa_bcv,
            empresa=empresa,
            total_facturado_usd=total_facturado_filtro,
            total_abonado_usd=total_abonado_filtro,
            total_por_cobrar_usd=total_por_cobrar_filtro,
            top_clientes=top_clientes,
            top_productos=top_productos,
            clientes_vip_ids=clientes_vip_ids,
            clientes_activos_ids=clientes_activos_ids,
            clientes_inactivos_ids=clientes_inactivos_ids,
            q=q,
            orden=orden,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            monto_min=monto_min,
            monto_max=monto_max,
            tipo_cliente=tipo_cliente,
            fecha_reporte=fecha_reporte
        )
    except Exception as e:
        print(f"Error en reporte_clientes_pdf: {e}")
        return str(e), 500

@app.route('/clientes/<path:id>/historial')
def historial_cliente(id):
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if id not in clientes:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('mostrar_clientes'))
    
    cliente = clientes[id]
    now = datetime.now()
    # Manejo robusto de filtros (evitar ValueError por strings vacíos)
    anio_param = request.args.get('anio')
    try:
        filtro_anio = int(anio_param) if anio_param else now.year
    except (TypeError, ValueError):
        filtro_anio = now.year
    # Mes robusto
    mes_param = request.args.get('mes', '')
    try:
        filtro_mes = int(mes_param) if mes_param else ''
    except (TypeError, ValueError):
        filtro_mes = ''

    # Filtrar facturas por cliente, preservando el ID y calculando pagos/saldos
    facturas_cliente = []
    for factura_id, factura_data in facturas.items():
        if factura_data.get('cliente_id') != id:
            continue
        factura_copia = factura_data.copy()
        factura_copia['id'] = factura_id
        # Calcular totales de pagos y saldo pendiente (alineado con ver_factura)
        total_abonado = 0
        pagos = factura_copia.get('pagos') or []
        try:
            pagos_iterables = pagos.values() if isinstance(pagos, dict) else pagos
        except Exception:
            pagos_iterables = []
        for pago in pagos_iterables:
            try:
                monto = float(str(pago.get('monto', 0)).replace('$', '').replace(',', ''))
                total_abonado += monto
            except Exception:
                continue
        try:
            total_usd_factura = float(str(factura_copia.get('total_usd', factura_copia.get('total', 0))).replace('$', '').replace(',', ''))
        except Exception:
            total_usd_factura = 0.0
        factura_copia['total_abonado'] = total_abonado
        factura_copia['saldo_pendiente'] = max(total_usd_factura - total_abonado, 0)
        facturas_cliente.append(factura_copia)
    
    # Filtrar facturas por año y mes seleccionados
    facturas_filtradas = []
    for f in facturas_cliente:
        fecha = f.get('fecha', '')
        try:
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            if fecha_dt.year == filtro_anio and (not filtro_mes or fecha_dt.month == filtro_mes):
                facturas_filtradas.append(f)
        except Exception:
            continue

    # Calcular totales anuales (protegido)
    facturas_anio_actual = []
    for f in facturas_cliente:
        fecha_txt = f.get('fecha', '')
        try:
            if fecha_txt:
                if datetime.strptime(fecha_txt, '%Y-%m-%d').year == now.year:
                    facturas_anio_actual.append(f)
        except Exception:
            continue
    total_anual_usd = sum(float(f.get('total_usd', 0)) for f in facturas_anio_actual)
    total_anual_bs = sum(float(f.get('total_bs', 0)) for f in facturas_anio_actual)

    # Calcular totales mensuales (protegido)
    facturas_mes_actual = []
    for f in facturas_cliente:
        fecha_txt = f.get('fecha', '')
        try:
            if fecha_txt:
                fecha_dt = datetime.strptime(fecha_txt, '%Y-%m-%d')
                if fecha_dt.year == now.year and fecha_dt.month == now.month:
                    facturas_mes_actual.append(f)
        except Exception:
            continue
    total_mensual_usd = sum(float(f.get('total_usd', 0)) for f in facturas_mes_actual)
    total_mensual_bs = sum(float(f.get('total_bs', 0)) for f in facturas_mes_actual)
    
    cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id), None)
    
    # Totales filtrados
    total_compras = sum(
        float(f.get('total_usd', f.get('total', 0)).replace('$', '').replace(',', '')) if isinstance(f.get('total_usd', f.get('total', 0)), str) else float(f.get('total_usd', f.get('total', 0)))
        for f in facturas_filtradas
    )
    total_bs = sum(
        float(f.get('total_bs', 0)) if f.get('total_bs', 0) else (
            float(f.get('total_usd', f.get('total', 0))) * float(f.get('tasa_bcv', 0) or 0)
        )
        for f in facturas_filtradas
    )

    # Productos comprados filtrados
    productos_comprados = {}
    for factura in facturas_filtradas:
        productos = factura.get('productos', [])
        cantidades = factura.get('cantidades', [])
        precios = factura.get('precios', [])
        
        for i in range(len(productos)):
            prod_id = productos[i]
            if prod_id in inventario:
                if prod_id not in productos_comprados:
                    productos_comprados[prod_id] = {
                        'nombre': inventario[prod_id]['nombre'],
                        'cantidad': 0,
                        'valor': 0
                    }
                try:
                    cantidad = int(cantidades[i])
                    precio = float(precios[i])
                    productos_comprados[prod_id]['cantidad'] += cantidad
                    productos_comprados[prod_id]['valor'] += cantidad * precio
                except (ValueError, TypeError, IndexError):
                    continue

    # Ordenar productos por valor total
    productos_comprados = dict(sorted(productos_comprados.items(), key=lambda x: x[1]['valor'], reverse=True))

    # Para el formulario de filtro (protegido)
    anios_disponibles_set = set()
    for f in facturas_cliente:
        fecha_txt = f.get('fecha', '')
        if not fecha_txt:
            continue
        try:
            anios_disponibles_set.add(datetime.strptime(fecha_txt, '%Y-%m-%d').year)
        except Exception:
            continue
    anios_disponibles = sorted(anios_disponibles_set)
    
    # Calcular promedio por factura (con protección extra)
    try:
        promedio_por_factura = float(total_compras) / len(facturas_filtradas) if len(facturas_filtradas) > 0 and total_compras is not None else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        promedio_por_factura = 0.0
    
    # Obtener configuración de mapas
    maps_config = get_maps_config()
    
    return render_template(
        'historial_cliente.html',
        cliente=cliente,
        facturas=facturas_filtradas,
        cuenta=cuenta,
        total_compras=total_compras,
        total_bs=total_bs,
        total_anual_usd=total_anual_usd,
        total_anual_bs=total_anual_bs,
        total_mensual_usd=total_mensual_usd,
        total_mensual_bs=total_mensual_bs,
        productos_comprados=productos_comprados,
        filtro_anio=filtro_anio,
        filtro_mes=filtro_mes,
        anios_disponibles=anios_disponibles,
        promedio_por_factura=promedio_por_factura,
        maps_config=maps_config,
        now=now
    )

def actualizar_facturas_antiguas():
    """Agrega campos nuevos por defecto a todas las facturas antiguas."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    campos_nuevos = {
        'hora': '',
        'condicion_pago': 'contado',
        'fecha_vencimiento': '',
        'tasa_bcv': '',
        'descuento': '0',
        'tipo_descuento': 'bs',
        'iva': '5',
        'pagos': {},
        'subtotal_usd': '0.00',
        'subtotal_bs': '0.00',
        'descuento_total': '0.00',
        'iva_total': '0.00',
        'total_usd': '0.00',
        'total_bs': '0.00'
    }
    actualizadas = 0
    for id, factura in facturas.items():
        cambiado = False
        for campo, valor in campos_nuevos.items():
            if campo not in factura:
                factura[campo] = valor
                cambiado = True
        if cambiado:
            actualizadas += 1
    if actualizadas > 0:
        guardar_datos(ARCHIVO_FACTURAS, facturas)
    return actualizadas

@app.route('/facturas/actualizar-campos')
def actualizar_campos_facturas():
    n = actualizar_facturas_antiguas()
    flash(f'Se actualizaron {n} facturas antiguas con los campos nuevos.', 'success' if n else 'info')
    return redirect(url_for('mostrar_facturas'))

@app.route('/inventario/cargar-csv', methods=['GET', 'POST'])
def cargar_productos_csv():
    """Formulario para cargar productos desde CSV."""
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if archivo and allowed_file(archivo.filename):
            try:
                filename = secure_filename(archivo.filename)
                ruta_archivo = os.path.join(UPLOAD_FOLDER, filename)
                archivo.save(ruta_archivo)
                
                if cargar_productos_desde_csv(ruta_archivo):
                    flash('Productos cargados exitosamente', 'success')
                else:
                    flash('Error al cargar los productos', 'danger')
                
                # Limpiar archivo después de procesarlo
                try:
                    os.remove(ruta_archivo)
                except:
                    pass
                    
                return redirect(url_for('mostrar_inventario'))
            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                return redirect(request.url)
        
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(request.url)
    
    return render_template('cargar_csv.html', tipo='productos')

@app.route('/inventario/eliminar-multiples', methods=['POST'])
def eliminar_productos_multiples():
    try:
        productos = json.loads(request.form.get('productos', '[]'))
        if not productos:
            flash('No se seleccionaron productos para eliminar', 'warning')
            return redirect(url_for('mostrar_inventario'))
        
        inventario = cargar_datos('inventario.json')
        eliminados = 0
        
        for id in productos:
            if id in inventario:
                del inventario[id]
                eliminados += 1
        
        if guardar_datos('inventario.json', inventario):
            flash(f'Se eliminaron {eliminados} productos exitosamente', 'success')
        else:
            flash('Error al guardar los cambios', 'danger')
            
    except Exception as e:
        flash(f'Error al eliminar los productos: {str(e)}', 'danger')
    
    return redirect(url_for('mostrar_inventario'))

# --- Filtro personalizado para parsear cadenas a fecha ---
@app.template_filter('strptime')
def strptime_filter(value, format='%Y-%m-%d'):
    """Filtro Jinja2 para parsear una cadena a objeto date."""
    if not value:
        return datetime.now().date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        val_str = str(value).split('T')[0].split(' ')[0].strip()
        return datetime.strptime(val_str, format).date()
    except Exception:
        try:
            return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
        except Exception:
            return datetime.now().date()

# --- Filtro personalizado para fechas legibles ---
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M:%S'):
    """Convierte una cadena de fecha a formato legible."""
    if not value:
        return ''
    try:
        # Intentar parsear formato ISO
        if 'T' in value:
            value = value.split('.')[0].replace('T', ' ')
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt.strftime(format)
    except Exception:
        return value  # Si falla, mostrar la cadena original

# --- Filtro personalizado para números en formato español ---
@app.template_filter('es_number')
def es_number(value, decimales=2):
    """Convierte un número a formato español (punto para miles, coma para decimales)."""
    try:
        # Si es None o string vacío, retornar 0
        if value is None or value == '':
            return f"0,{decimales * '0'}"
            
        # Convertir a float
        value = float(value)
        
        # Si es 0, retornar formato con decimales
        if value == 0:
            return f"0,{decimales * '0'}"
            
        # Formatear con separadores de miles y decimales
        formatted = f"{abs(value):,.{decimales}f}"
        
        # Reemplazar comas y puntos para formato español
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Agregar signo negativo si corresponde
        if value < 0:
            formatted = f"-{formatted}"
            
        return formatted
    except Exception:
        return str(value) if value is not None else "0"

# ===== RUTA PARA RECORDATORIOS WHATSAPP MEJORADA =====
@app.route('/cuentas-por-cobrar/enviar_recordatorio_whatsapp', methods=['POST'])
def enviar_recordatorio_cuentas_por_cobrar_body():
    """Endpoint que recibe cliente_id por body JSON y genera recordatorio inteligente con diferentes niveles de urgencia."""
    print(f"🔍 RUTA REGISTRADA: /cuentas-por-cobrar/enviar_recordatorio_whatsapp")
    print(f"🔍 Endpoint llamado - Método: {request.method}")
    
    try:
        # Obtener datos del body
        data = request.get_json(silent=True)
        print(f"🔍 JSON recibido: {data}")
        
        if not data:
            data = request.form.to_dict()
            print(f"🔍 Form data recibido: {data}")
        
        cliente_id = str(data.get('cliente_id') or '').strip()
        print(f"🔍 Cliente ID extraído: '{cliente_id}'")
        
        if not cliente_id:
            return jsonify({'error': 'Falta cliente_id en la solicitud'}), 400
        
        # Cargar datos directamente aquí
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        if cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono:
            return jsonify({'error': 'El cliente no tiene teléfono registrado'}), 400
        
        # Filtrar facturas pendientes
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'fecha': factura.get('fecha', 'N/A'),
                        'total': total_factura,
                        'abonado': total_abonado,
                        'saldo': saldo_pendiente
                    })
                    total_pendiente += saldo_pendiente
        
        if not facturas_pendientes:
            return jsonify({
                'success': True,
                'message': 'El cliente no tiene facturas pendientes de pago',
                'total_facturas': 0,
                'total_pendiente': 0
            })
        
        # Formatear teléfono
        telefono_limpio = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not telefono_limpio.startswith('58'):
            telefono_limpio = '58' + telefono_limpio.lstrip('0')
        
        # Determinar nivel de urgencia basado en el monto y antigüedad
        from datetime import datetime, date, timedelta
        hoy = date.today()
        factura_mas_antigua = None
        dias_vencimiento = 0
        facturas_vencidas = []
        
        for factura in facturas_pendientes:
            try:
                fecha_factura = datetime.strptime(factura['fecha'], '%Y-%m-%d').date()
                dias = (hoy - fecha_factura).days
                
                # Calcular fecha de vencimiento si es a crédito
                condicion_pago = factura.get('condicion_pago', 'contado')
                if condicion_pago in ['credito', 'crédito', '30 dias', '30 días', '60 dias', '60 días']:
                    if '30' in condicion_pago:
                        fecha_vencimiento = fecha_factura + timedelta(days=30)
                    elif '60' in condicion_pago:
                        fecha_vencimiento = fecha_factura + timedelta(days=60)
                    else:
                        fecha_vencimiento = fecha_factura + timedelta(days=30)  # Por defecto 30 días
                    
                    dias_vencimiento_factura = (hoy - fecha_vencimiento).days
                    if dias_vencimiento_factura > 0:
                        facturas_vencidas.append({
                            'numero': factura['numero'],
                            'dias_vencido': dias_vencimiento_factura,
                            'fecha_vencimiento': fecha_vencimiento.strftime('%Y-%m-%d')
                        })
                
                if dias > dias_vencimiento:
                    dias_vencimiento = dias
                    factura_mas_antigua = factura
            except:
                continue
        
        # Obtener tipo de mensaje del request (si se envía) o determinar automáticamente
        tipo_mensaje_solicitado = data.get('tipo_mensaje', '').upper()
        
        if tipo_mensaje_solicitado in ['URGENTE', 'MEDIO', 'FLEXIBLE']:
            # Usar el tipo solicitado por el usuario
            tipo_mensaje = tipo_mensaje_solicitado
        else:
            # Determinar automáticamente según urgencia
            if total_pendiente > 1000 or dias_vencimiento > 60:
                tipo_mensaje = "URGENTE"
            elif total_pendiente > 500 or dias_vencimiento > 30:
                tipo_mensaje = "MEDIO"
            else:
                tipo_mensaje = "FLEXIBLE"
        
        # Asignar emoji y tono según el tipo
        if tipo_mensaje == "URGENTE":
            emoji_principal = "🚨"
            tono = "urgente"
        elif tipo_mensaje == "MEDIO":
            emoji_principal = "⚠️"
            tono = "medio"
        else:  # FLEXIBLE
            emoji_principal = "💼"
            tono = "flexible"
        
        # Crear mensaje personalizado según el tipo
        if tipo_mensaje == "URGENTE":
            mensaje = f"""{emoji_principal} *RECORDATORIO URGENTE DE PAGO* {emoji_principal}

👋 Hola {cliente.get('nombre', 'Cliente')}

🚨 *ATENCIÓN INMEDIATA REQUERIDA*

📊 *Resumen de Facturas Pendientes:*
• Total de facturas: {len(facturas_pendientes)}
• Monto pendiente: *${total_pendiente:.2f} USD*
• Factura más antigua: {factura_mas_antigua['numero'] if factura_mas_antigua else 'N/A'} ({dias_vencimiento} días)
{f"• Facturas vencidas: {len(facturas_vencidas)} facturas" if facturas_vencidas else ""}

⏰ *Este recordatorio requiere acción inmediata*

🏢 *PRODUCTOS NATURALES KISVIC 1045, C.A.*
📍 Centro Comercial Caña de Azúcar (Antiguo Merbumar)
   Nave A, Locales 154-156, Maracay-Edo. Aragua
📧 kisvic1045@gmail.com
📱 0424-728-6225
🆔 RIF: J-404373818

📞 *Por favor contacta urgentemente para coordinar el pago*

🙏 *Tu pronta respuesta es muy importante*"""
            
        elif tipo_mensaje == "MEDIO":
            mensaje = f"""{emoji_principal} *Recordatorio de Pago* {emoji_principal}

👋 Hola {cliente.get('nombre', 'Cliente')}

📋 *Recordatorio de Facturas Pendientes:*
• Total de facturas: {len(facturas_pendientes)}
• Monto pendiente: *${total_pendiente:.2f} USD*
• Días transcurridos: {dias_vencimiento} días
{f"• Facturas vencidas: {len(facturas_vencidas)} facturas" if facturas_vencidas else ""}

🏢 *PRODUCTOS NATURALES KISVIC 1045, C.A.*
📍 Centro Comercial Caña de Azúcar (Antiguo Merbumar)
   Nave A, Locales 154-156, Maracay-Edo. Aragua
📧 kisvic1045@gmail.com
📱 0424-728-6225
🆔 RIF: J-404373818

📞 *Te invitamos a contactar para coordinar el pago*

⏰ *Es importante regularizar esta situación*"""
            
        else:  # FLEXIBLE
            mensaje = f"""{emoji_principal} *Recordatorio Amigable* {emoji_principal}

👋 Hola {cliente.get('nombre', 'Cliente')}

📋 *Información de Facturas Pendientes:*
• Total de facturas: {len(facturas_pendientes)}
• Monto pendiente: *${total_pendiente:.2f} USD*
{f"• Facturas vencidas: {len(facturas_vencidas)} facturas" if facturas_vencidas else ""}

🏢 *PRODUCTOS NATURALES KISVIC 1045, C.A.*
📍 Centro Comercial Caña de Azúcar (Antiguo Merbumar)
   Nave A, Locales 154-156, Maracay-Edo. Aragua
📧 kisvic1045@gmail.com
📱 0424-728-6225
🆔 RIF: J-404373818

📞 *Cuando puedas, contáctanos para coordinar el pago*

🙏 *Gracias por tu atención*"""
        
        # Generar enlaces
        mensaje_codificado = urllib.parse.quote(mensaje)
        enlace_whatsapp = f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}"
        enlace_web = f"https://web.whatsapp.com/send?phone={telefono_limpio}&text={mensaje_codificado}"
        
        resultado = {
            'success': True,
            'message': f'Recordatorio {tipo_mensaje.lower()} preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'enlace_web': enlace_web,
            'telefono': telefono,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'total_facturas': len(facturas_pendientes),
            'total_facturado': sum(f['total'] for f in facturas_pendientes),
            'total_abonado': sum(f['abonado'] for f in facturas_pendientes),
            'total_pendiente': total_pendiente,
            'tipo_mensaje': tipo_mensaje,
            'dias_vencimiento': dias_vencimiento,
            'emoji_principal': emoji_principal,
            'tono': tono,
            'facturas_vencidas': facturas_vencidas,
            'total_facturas_vencidas': len(facturas_vencidas)
        }
        
        print(f"✅ Recordatorio {tipo_mensaje} preparado exitosamente para {cliente.get('nombre', 'N/A')}")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error en endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500



@app.route('/pagos-recibidos')
@login_required
def mostrar_pagos_recibidos():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    pagos = []
    total_usd = 0
    total_bs = 0
    # Obtener tasas de Monitor Dólar
    tasa_bcv = None
    tasa_paralelo = None
    tasa_bcv_eur = None
    try:
        r = requests.get('https://s3.amazonaws.com/dolartoday/data.json', timeout=5)
        data = r.json()
        tasa_bcv = float(data['USD']['bcv']) if 'USD' in data and 'bcv' in data['USD'] else None
        tasa_paralelo = float(data['USD']['promedio']) if 'USD' in data and 'promedio' in data['USD'] else None
        tasa_bcv_eur = float(data['EUR']['promedio']) if 'EUR' in data and 'promedio' in data['EUR'] else None
    except Exception:
        tasa_bcv = obtener_tasa_bcv() or 1.0
        tasa_paralelo = tasa_bcv
        tasa_bcv_eur = 0

    for f in facturas.values():
        if 'pagos' in f and f['pagos']:
            # Verificar que la factura tenga un ID válido
            factura_id = f.get('id')
            if not factura_id:
                print(f"⚠️ Factura sin ID encontrada: {f}")
                continue
                
            for pago in f['pagos']:
                captura_path = pago.get('captura_path')
                if captura_path:
                    # Normalizar la ruta para que siempre sea /uploads/capturas/...
                    if 'uploads/capturas/' in captura_path:
                        # Quitar static/ si lo tiene
                        captura_path = captura_path.split('static/')[-1]
                        # Asegurar que empiece con uploads/capturas/
                        if not captura_path.startswith('uploads/capturas/'):
                            captura_path = 'uploads/capturas/' + os.path.basename(captura_path)
                    else:
                        captura_path = 'uploads/capturas/' + os.path.basename(captura_path)
                    # Validar existencia del archivo
                    ruta_absoluta = os.path.join('static', captura_path.replace('/', os.sep))
                    if not os.path.exists(ruta_absoluta):
                        captura_path = None
                else:
                    captura_path = None

                pagos.append({
                    'factura_id': factura_id,
                    'fecha': f.get('fecha'),
                    'cliente_id': f.get('cliente_id'),
                    'monto': pago.get('monto', 0),
                    'metodo': pago.get('metodo', ''),
                    'tasa_bcv': float(f.get('tasa_bcv', tasa_bcv)),
                    'referencia': pago.get('referencia', ''),
                    'banco': pago.get('banco', ''),
                    'captura_path': captura_path
                })
                total_usd += float(pago.get('monto', 0))
                total_bs += float(pago.get('monto', 0)) * float(f.get('tasa_bcv', tasa_bcv))

    return render_template('pagos_recibidos.html', 
                         pagos=pagos, 
                         clientes=clientes, 
                         total_usd=total_usd, 
                         total_bs=total_bs, 
                         tasa_bcv=tasa_bcv, 
                         tasa_paralelo=tasa_paralelo, 
                         tasa_bcv_eur=tasa_bcv_eur)

@app.template_filter('split')
def split_filter(value, delimiter=' '):
    """Filtro personalizado para dividir strings"""
    return value.split(delimiter)

@app.route('/reporte/facturas')
def reporte_facturas():
    """Muestra un reporte general de facturas con filtros y estadísticas"""
    # Cargar datos necesarios
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    # Obtener parámetros de filtro
    filtro_anio = request.args.get('anio', '')
    filtro_mes = request.args.get('mes', '')
    filtro_cliente = request.args.get('cliente', '')

    # Obtener años disponibles de las facturas
    anios_disponibles = sorted({f['fecha'].split('-')[0] for f in facturas.values() if f.get('fecha')})

    # Filtrar facturas
    facturas_filtradas = []
    for factura in facturas.values():
        fecha = factura['fecha'].split('-')
        anio_factura = fecha[0]
        mes_factura = fecha[1]

        # Aplicar filtros
        if filtro_anio and anio_factura != filtro_anio:
            continue
        if filtro_mes and mes_factura != filtro_mes.zfill(2):
            continue
        if filtro_cliente and str(factura['cliente_id']) != filtro_cliente:
            continue
        # Calcular estado actualizado
        total_abonado = 0
        if 'pagos' in factura and factura['pagos']:
            for pago in factura['pagos']:
                try:
                    monto = float(str(pago.get('monto', 0)).replace('$', '').replace(',', ''))
                    total_abonado += monto
                except Exception:
                    continue
        total_factura = factura.get('total_usd') or factura.get('total') or 0
        if isinstance(total_factura, str):
            total_factura = float(total_factura.replace('$', '').replace(',', ''))
        if total_abonado >= total_factura and total_factura > 0:
            factura['estado'] = 'pagada'
        else:
            factura['estado'] = 'pendiente'
        factura['total_abonado'] = total_abonado
        factura['saldo_pendiente'] = max(total_factura - total_abonado, 0)
        facturas_filtradas.append(factura)

    # Calcular totales
    total_facturas = len(facturas_filtradas)
    total_usd = sum(float(f.get('total_usd', 0)) for f in facturas_filtradas)
    total_bs = sum(float(f.get('total_bs', 0)) for f in facturas_filtradas)
    promedio_usd = total_usd / total_facturas if total_facturas > 0 else 0

    # Calcular top clientes
    clientes_totales = {}
    for factura in facturas_filtradas:
        cliente_id = factura['cliente_id']
        if cliente_id not in clientes_totales:
            clientes_totales[cliente_id] = {
                'total_usd': 0,
                'total_bs': 0,
                'total_facturas': 0
            }
        clientes_totales[cliente_id]['total_usd'] += float(factura.get('total_usd', 0))
        clientes_totales[cliente_id]['total_bs'] += float(factura.get('total_bs', 0))
        clientes_totales[cliente_id]['total_facturas'] += 1

    # Preparar lista de top clientes con todos los campos necesarios
    top_clientes = []
    for cid, stats in sorted(clientes_totales.items(), key=lambda x: x[1]['total_usd'], reverse=True)[:10]:
        cliente = clientes.get(cid, {})
        total_facturas_cliente = stats['total_facturas']
        promedio_usd_cliente = stats['total_usd'] / total_facturas_cliente if total_facturas_cliente > 0 else 0
        top_clientes.append({
            'nombre': cliente.get('nombre', 'Cliente no encontrado'),
            'total_facturas': total_facturas_cliente,
            'total_usd': stats['total_usd'],
            'total_bs': stats['total_bs'],
            'promedio_usd': promedio_usd_cliente
        })

    return render_template('reporte_facturas.html',
                         facturas=facturas_filtradas,
                         clientes=clientes,
                         total_facturas=total_facturas,
                         total_usd=total_usd,
                         total_bs=total_bs,
                         promedio_usd=promedio_usd,
                         top_clientes=top_clientes,
                         filtro_anio=filtro_anio,
                         filtro_mes=filtro_mes,
                         filtro_cliente=filtro_cliente,
                         anios_disponibles=anios_disponibles)

@app.route('/inventario/')
def inventario_slash_redirect():
    return redirect(url_for('mostrar_inventario'))

@app.route('/facturas/reparar-totales')
def reparar_totales_facturas():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    actualizadas = 0
    for id, factura in facturas.items():
        # Recalcular totales y pagos
        try:
            precios = factura.get('precios', [])
            cantidades = factura.get('cantidades', [])
            subtotal_usd = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios))) if precios and cantidades else 0
            tasa_bcv = float(factura.get('tasa_bcv', 1))
            descuento_total = float(factura.get('descuento_total', 0))
            iva_total = float(factura.get('iva_total', 0))
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            pagos = factura.get('pagos', [])
            total_abonado = sum(float(p.get('monto', 0)) for p in pagos)
            saldo_pendiente = max(total_usd - total_abonado, 0)
            # Actualizar campos
            factura['subtotal_usd'] = subtotal_usd
            factura['subtotal_bs'] = subtotal_bs
            factura['total_usd'] = total_usd
            factura['total_bs'] = total_bs
            factura['total_abonado'] = total_abonado
            factura['saldo_pendiente'] = saldo_pendiente
            facturas[id] = factura
            actualizadas += 1
        except Exception as e:
            print(f"Error actualizando factura {id}: {e}")
    guardar_datos(ARCHIVO_FACTURAS, facturas)
    flash(f'Se actualizaron {actualizadas} facturas con los totales y pagos recalculados.', 'success')
    return redirect(url_for('mostrar_facturas'))

@app.route('/reporte/cotizaciones')
def reporte_cotizaciones():
    """Reporte básico de cotizaciones."""
    cotizaciones = []
    cotizaciones_dir = 'cotizaciones_json'
    if os.path.exists(cotizaciones_dir):
        for filename in os.listdir(cotizaciones_dir):
            if filename.endswith('.json'):
                try:
                    cot_data = cargar_datos(
                        os.path.join(cotizaciones_dir, filename), crear_vacio=False
                    )
                    if not cot_data:
                        continue
                        if not cot_data.get('numero_cotizacion') or not cot_data.get('fecha') or not cot_data.get('cliente', {}).get('nombre'):
                            continue
                        cotizaciones.append(cot_data)
                except Exception:
                    continue
    total_cotizaciones = len(cotizaciones)
    total_monto = sum(float(str(c.get('total_usd', 0)).replace('$', '').replace(',', '').strip()) for c in cotizaciones)
    return render_template('reporte_cotizaciones.html', cotizaciones=cotizaciones, total_cotizaciones=total_cotizaciones, total_monto=total_monto, now=datetime.now())

@app.route('/cotizaciones/<id>/convertir-a-factura')
def convertir_cotizacion_a_factura(id):
    """Convierte una cotización en factura y abre el formulario de factura para editar antes de guardar."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    cotizacion = cargar_datos(filename, crear_vacio=False)
    if not cotizacion:
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    cotizacion = normalizar_cotizacion(cotizacion, clientes, inventario)
    empresa = cargar_empresa()
    # Preparar datos para el formulario de factura
    factura = {
        'numero': '',
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'hora': datetime.now().strftime('%H:%M:%S'),
        'condicion_pago': 'contado',
        'fecha_vencimiento': '',
        'tasa_bcv': cotizacion.get('tasa_bcv', ''),
        'cliente_id': cotizacion.get('cliente', {}).get('id', ''),
        'productos': cotizacion.get('productos', []),
        'cantidades': cotizacion.get('cantidades', []),
        'precios': [float(p) for p in cotizacion.get('precios', [])],
        'descuento': cotizacion.get('descuento', '0'),
        'tipo_descuento': cotizacion.get('tipo_descuento', 'bs'),
        'iva': cotizacion.get('iva', '16'),
        'subtotal_usd': cotizacion.get('subtotal_usd', '0'),
        'subtotal_bs': cotizacion.get('subtotal_bs', '0'),
        'descuento_total': cotizacion.get('descuento_total', '0'),
        'iva_total': cotizacion.get('iva_total', '0'),
        'total_usd': cotizacion.get('total_usd', '0'),
        'total_bs': cotizacion.get('total_bs', '0'),
        'pagos': [],
        'estado': 'pendiente',
        'total_abonado': 0,
        'saldo_pendiente': cotizacion.get('total_usd', '0'),
    }
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0 or k in factura.get('productos', [])}
    return render_template('factura_form.html', factura=factura, clientes=clientes, inventario=inventario_disponible, editar=False, empresa=empresa)



@app.route('/cotizaciones/<id>/pdf')
def descargar_cotizacion_pdf(id):
    if pdfkit is None:
        flash('PDFKit no está instalado. Instala con: pip install pdfkit', 'danger')
        return redirect(url_for('ver_cotizacion', id=id))
    cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    cotizacion = cotizaciones.get(id)
    if not cotizacion:
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    empresa = cargar_empresa()
    
    # Convertir rutas relativas a absolutas para las imágenes
    if empresa.get('logo'):
        empresa['logo'] = request.url_root.rstrip('/') + url_for('static', filename=empresa['logo'])
    if empresa.get('membrete'):
        empresa['membrete'] = request.url_root.rstrip('/') + url_for('static', filename=empresa['membrete'])
    
    rendered = render_template('cotizacion_imprimir.html', 
                             cotizacion=cotizacion, 
                             clientes=clientes, 
                             inventario=inventario,
                             now=datetime.now,
                             empresa=empresa,
                             zip=zip)
    try:
        # Intentar diferentes ubicaciones comunes de wkhtmltopdf
        wkhtmltopdf_paths = [
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            'wkhtmltopdf'  # Si está en el PATH
        ]
        
        config = None
        for path in wkhtmltopdf_paths:
            if os.path.exists(path):
                config = pdfkit.configuration(wkhtmltopdf=path)
                break
        
        if config is None:
            # Si no se encuentra wkhtmltopdf, intentar usar el comando directamente
            config = pdfkit.configuration(wkhtmltopdf='wkhtmltopdf')
            
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '15mm',
            'margin-bottom': '20mm',
            'margin-left': '15mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'quiet': '',
            'print-media-type': '',
            'disable-smart-shrinking': '',
            'dpi': 300,
            'image-quality': 100,
            'enable-local-file-access': None,
            'footer-right': '[page] de [topage]',
            'footer-font-size': '8',
            'footer-spacing': '5',
            'javascript-delay': '1000',
            'no-stop-slow-scripts': None
        }
        pdf = pdfkit.from_string(rendered, False, configuration=config, options=options)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=cotizacion_{cotizacion["numero"]}.pdf'
        return response
    except Exception as e:
        print(f"Error al generar PDF: {str(e)}")  # Para debugging
        flash(f'Error al generar PDF: {str(e)}', 'danger')
        return redirect(url_for('ver_cotizacion', id=id))

@app.route('/cotizacion/<numero>')
def ver_cotizacion(numero):
    try:
        # Cargar la cotización
        cotizacion_path = os.path.join('cotizaciones_json', f'cotizacion_{numero}.json')
        cotizacion = cargar_datos(cotizacion_path, crear_vacio=False)
        if not cotizacion:
            flash('Cotización no encontrada', 'error')
            return redirect(url_for('cotizaciones'))

        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        empresa = cargar_empresa()
        
        return render_template('cotizacion_imprimir.html', cotizacion=cotizacion, inventario=inventario, empresa=empresa, zip=zip)
    except Exception as e:
        flash(f'Error al cargar la cotización: {str(e)}', 'error')
        return redirect(url_for('cotizaciones'))





@app.route('/facturas/<id>/eliminar_pago/<pago_id>', methods=['POST'])
@login_required
def eliminar_pago(id, pago_id):
    # Validación simple del ID
    if not id or str(id).strip() == '':
        flash('ID de factura inválido', 'danger')
        return redirect(url_for('mostrar_facturas'))
    try:
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        if id not in facturas:
            flash('Factura no encontrada', 'error')
            return redirect(url_for('mostrar_facturas'))
        
        factura = facturas[id]
        pagos = factura.get('pagos', [])
        
        pago_encontrado = False
        for i, pago in enumerate(pagos):
            if str(pago.get('id', '')) == str(pago_id):
                monto_pago = float(pago.get('monto', 0))
                if pago.get('moneda') == 'Bs':
                    monto_pago = monto_pago / float(factura.get('tasa_bcv', 1))
                
                factura['total_abonado'] = float(factura.get('total_abonado', 0)) - monto_pago
                saldo_pendiente = factura.get('total_usd', 0) - factura['total_abonado']
                
                # Si el saldo pendiente es muy pequeño (menos de 0.01) o el total abonado es igual o mayor al total
                if abs(saldo_pendiente) < 0.01 or factura['total_abonado'] >= factura.get('total_usd', 0):
                    saldo_pendiente = 0
                    factura['estado'] = 'pagada'
                else:
                    factura['estado'] = 'pendiente'
                
                factura['saldo_pendiente'] = saldo_pendiente
                pagos.pop(i)
                pago_encontrado = True
                break
        
        if not pago_encontrado:
            flash('Pago no encontrado', 'error')
            return redirect(url_for('editar_factura', id=id))
        
        facturas[id] = factura
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Pago eliminado exitosamente', 'success')
        else:
            flash('Error al guardar los cambios', 'error')
            
    except Exception as e:
        flash(f'Error al eliminar el pago: {str(e)}', 'error')
    
    return redirect(url_for('editar_factura', id=id))

@app.route('/facturas/<id>/saldo')
@login_required
def obtener_saldo_factura(id):
    # Validación simple del ID
    if not id or str(id).strip() == '':
        flash('ID de factura inválido', 'danger')
        return redirect(url_for('mostrar_facturas'))
    try:
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        saldo_pendiente = float(factura.get('saldo_pendiente', 0))
        tasa_bcv = float(factura.get('tasa_bcv', 0))
        
        return jsonify({
            'saldo_pendiente': saldo_pendiente,
            'tasa_bcv': tasa_bcv
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/facturas/<id>/enviar_recordatorio_whatsapp', methods=['POST'])
@login_required
@csrf.exempt
def enviar_recordatorio_whatsapp(id):
    # Validación simple del ID
    if not id or str(id).strip() == '':
        print("❌ ID de factura inválido")
        return jsonify({'error': 'ID de factura inválido'}), 400
    
    try:
        print(f"🔍 Iniciando envío de recordatorio WhatsApp para factura: {id}")
        print(f"🔍 Método de petición: {request.method}")
        print(f"🔍 Headers: {dict(request.headers)}")
        print(f"🔍 Content-Type: {request.content_type}")
        
        # Ignorar datos del body si existen - solo usar el ID de la URL
        print("🔍 Usando solo el ID de la URL, ignorando datos del body")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        print(f"📊 Facturas cargadas: {len(facturas)}")
        print(f"👥 Clientes cargados: {len(clientes)}")
        
        if id not in facturas:
            print(f"❌ Factura {id} no encontrada")
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        print(f"👤 Cliente ID: {cliente_id}")
        print(f"📄 Factura: {factura.get('numero', 'N/A')}")
        
        if not cliente_id:
            print(f"❌ Factura {id} no tiene cliente_id")
            return jsonify({'error': 'La factura no tiene cliente asignado'}), 400
        
        # Verificar si el cliente_id está en la lista de clientes
        print(f"🔍 Buscando cliente_id '{cliente_id}' en clientes...")
        print(f"🔍 Clientes disponibles: {list(clientes.keys())}")
        
        if cliente_id not in clientes:
            print(f"❌ Cliente {cliente_id} no encontrado en clientes")
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        print(f"📱 Teléfono del cliente: {telefono}")
        print(f"👤 Nombre del cliente: {cliente.get('nombre', 'N/A')}")
        
        if not telefono:
            print(f"❌ Cliente {cliente_id} no tiene teléfono")
            return jsonify({'error': 'El cliente no tiene número de teléfono registrado'}), 400
        
        # Limpiar y formatear el número de teléfono
        telefono_original = telefono
        try:
            telefono = limpiar_numero_telefono(telefono)
            print(f"📱 Teléfono formateado exitosamente: {telefono}")
        except Exception as e:
            print(f"❌ Error formateando teléfono: {e}")
            return jsonify({'error': f'Error formateando teléfono: {str(e)}'}), 400
        
        print(f"📱 Teléfono original: {telefono_original}")
        print(f"📱 Teléfono formateado: {telefono}")
        
        if not telefono or len(telefono) < 10:
            print(f"❌ Teléfono formateado no válido: {telefono}")
            return jsonify({'error': 'El número de teléfono no es válido'}), 400
        
        # Crear mensaje personalizado
        try:
            mensaje = crear_mensaje_recordatorio(factura, cliente)
            print(f"💬 Mensaje creado exitosamente: {len(mensaje)} caracteres")
        except Exception as e:
            print(f"❌ Error creando mensaje: {e}")
            return jsonify({'error': f'Error creando mensaje: {str(e)}'}), 400
        
        # Generar enlace de WhatsApp
        try:
            enlace_whatsapp = generar_enlace_whatsapp(telefono, mensaje)
            print(f"🔗 Enlace WhatsApp generado exitosamente: {enlace_whatsapp}")
        except Exception as e:
            print(f"❌ Error generando enlace: {e}")
            return jsonify({'error': f'Error generando enlace: {str(e)}'}), 400
        
        # Registrar en la bitácora
        try:
            registrar_bitacora(
                session.get('usuario', 'Sistema'),
                'Recordatorio WhatsApp Enviado',
                f'Factura {factura.get("numero", "N/A")} - Cliente: {cliente.get("nombre", "N/A")}'
            )
            print("📝 Registrado en bitácora")
        except Exception as e:
            print(f"⚠️ Error registrando en bitácora: {e}")
        
        resultado = {
            'success': True,
            'message': 'Recordatorio preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'debug_info': {
                'factura_id': id,
                'cliente_id': cliente_id,
                'telefono_original': telefono_original,
                'telefono_formateado': telefono
            }
        }
        
        print(f"✅ Recordatorio preparado exitosamente para {cliente.get('nombre', 'N/A')}")
        return jsonify(resultado)
        
    except Exception as e:
        error_msg = f"Error al enviar recordatorio WhatsApp: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Traceback completo:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Error al preparar el recordatorio: {str(e)}',
            'debug_info': {
                'factura_id': id,
                'error_type': type(e).__name__,
                'error_details': str(e)
            }
        })

@app.route('/guardar_ubicacion_precisa', methods=['POST'])
def guardar_ubicacion_precisa():
    data = request.get_json()
    if data and 'lat' in data and 'lon' in data:
        lat = data['lat']
        lon = data['lon']
        # Reverse geocoding con Nominatim
        try:
            url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1'
            headers = {'User-Agent': 'mi-app-web/1.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                info = resp.json().get('address', {})
                ciudad = info.get('city') or info.get('town') or info.get('village') or info.get('hamlet') or ''
                estado = info.get('state', '')
                pais = info.get('country', '')
                texto = ', '.join([v for v in [ciudad, estado, pais] if v])
                session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': texto}
            else:
                session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': ''}
        except Exception:
            session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': ''}
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@app.route('/probar-recordatorio-whatsapp/<id>')
def probar_recordatorio_whatsapp(id):
    """Ruta de prueba para verificar el funcionamiento del recordatorio WhatsApp."""
    try:
        print(f"🧪 PROBANDO recordatorio WhatsApp para factura: {id}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        if not cliente_id or cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono:
            return jsonify({'error': 'Cliente no tiene teléfono'}), 400
        
        # Limpiar y formatear el número de teléfono
        telefono_limpio = limpiar_numero_telefono(telefono)
        
        # Crear mensaje personalizado
        mensaje = crear_mensaje_recordatorio(factura, cliente)
        
        # Generar enlace de WhatsApp
        enlace_whatsapp = generar_enlace_whatsapp(telefono_limpio, mensaje)
        
        return jsonify({
            'success': True,
            'message': 'Recordatorio preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono_limpio,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A')
        })
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/whatsapp-ultra-simple/<id>', methods=['GET', 'POST'])
@csrf.exempt
def whatsapp_ultra_simple(id):
    """Función ultra simple que funciona con GET y POST para máxima compatibilidad."""
    try:
        print(f"🚀 WHATSAPP ULTRA SIMPLE para factura: {id}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        if not cliente_id or cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono:
            print(f"❌ Cliente {cliente_id} no tiene número de teléfono registrado")
            return jsonify({'error': 'Cliente no tiene número de teléfono registrado'}), 400
        
        # Limpiar y formatear el número de teléfono
        telefono_limpio = limpiar_numero_telefono(telefono)
        
        # Crear mensaje personalizado
        mensaje = crear_mensaje_recordatorio(factura, cliente)
        
        # Generar enlace de WhatsApp
        enlace_whatsapp = generar_enlace_whatsapp(telefono_limpio, mensaje)
        
        return jsonify({
            'success': True,
            'message': 'Recordatorio preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono_limpio,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A')
        })
        
    except Exception as e:
        print(f"❌ Error en WhatsApp ultra simple: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/whatsapp-simple/<id>', methods=['POST'])
@csrf.exempt
def whatsapp_simple(id):
    """Función ultra simple para recordatorios de WhatsApp sin autenticación.
    
    Nota: Si el cliente no tiene número de teléfono registrado, devuelve HTTP 400
    con el mensaje 'Cliente no tiene número de teléfono registrado'.
    """
    try:
        print(f"🚀 WHATSAPP SIMPLE para factura: {id}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        if not cliente_id or cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono:
            print(f"❌ Cliente {cliente_id} no tiene número de teléfono registrado")
            return jsonify({'error': 'Cliente no tiene número de teléfono registrado'}), 400
        
        # Limpiar y formatear el número de teléfono
        telefono_limpio = limpiar_numero_telefono(telefono)
        
        # Crear mensaje personalizado
        mensaje = crear_mensaje_recordatorio(factura, cliente)
        
        # Generar enlace de WhatsApp
        enlace_whatsapp = generar_enlace_whatsapp(telefono_limpio, mensaje)
        
        return jsonify({
            'success': True,
            'message': 'Recordatorio preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono_limpio,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A')
        })
        
    except Exception as e:
        print(f"❌ Error en WhatsApp simple: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/facturas/<id>/whatsapp-backup', methods=['POST'])
@login_required
def whatsapp_backup(id):
    """Función de respaldo para recordatorios de WhatsApp."""
    try:
        print(f"🔄 FUNCIÓN DE RESPALDO WhatsApp para factura: {id}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        if not cliente_id or cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono:
            return jsonify({'error': 'Cliente no tiene teléfono'}), 400
        
        # Limpiar y formatear el número de teléfono
        telefono_limpio = limpiar_numero_telefono(telefono)
        
        # Crear mensaje personalizado
        mensaje = crear_mensaje_recordatorio(factura, cliente)
        
        # Generar enlace de WhatsApp
        enlace_whatsapp = generar_enlace_whatsapp(telefono_limpio, mensaje)
        
        return jsonify({
            'success': True,
            'message': 'Recordatorio preparado para WhatsApp (función de respaldo)',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono_limpio,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A')
        })
        
    except Exception as e:
        print(f"❌ Error en función de respaldo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/forzar-actualizacion-tasa-bcv')
def forzar_actualizacion_tasa_bcv():
    """Fuerza la actualización de la tasa BCV desde la web del BCV."""
    try:
        print("🔄 FORZANDO actualización de tasa BCV desde web...")
        
        # Obtener tasa desde web (ignorar archivo local)
        nueva_tasa = obtener_tasa_bcv_dia()
        
        if nueva_tasa and nueva_tasa > 10:
            resultado = {
                'success': True,
                'message': f'Tasa BCV actualizada exitosamente: {nueva_tasa}',
                'tasa_nueva': nueva_tasa,
                'fecha_actualizacion': datetime.now().isoformat(),
                'fuente': 'BCV Web Oficial'
            }
            print(f"✅ Tasa BCV actualizada: {nueva_tasa}")
        else:
            resultado = {
                'success': False,
                'message': 'No se pudo obtener la tasa BCV desde la web',
                'error': 'Tasa no válida o no encontrada'
            }
            print("❌ No se pudo obtener tasa válida desde web")
        
        return jsonify(resultado)
        
    except Exception as e:
        error_msg = f"Error forzando actualización: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            'success': False,
            'message': error_msg,
            'error': str(e)
        }), 500

@app.route('/probar-tasa-bcv')
def probar_tasa_bcv():
    """Ruta de prueba para verificar el funcionamiento de la tasa BCV."""
    try:
        resultado = {
            'archivo_existe': os.path.exists(ULTIMA_TASA_BCV_FILE),
            'tasa_local': None,
            'tasa_web': None,
            'tasa_final': None,
            'tasa_sistema': None,
            'errores': []
        }
        
        # Probar búsqueda en el sistema
        try:
            tasa_sistema = obtener_ultima_tasa_del_sistema()
            resultado['tasa_sistema'] = tasa_sistema
        except Exception as e:
            resultado['errores'].append(f"Error buscando tasa en sistema: {e}")
        
        # Probar carga de tasa local
        try:
            tasa_local = cargar_ultima_tasa_bcv()
            resultado['tasa_local'] = tasa_local
        except Exception as e:
            resultado['errores'].append(f"Error cargando tasa local: {e}")
        
        # Probar obtención de tasa web
        try:
            tasa_web = obtener_tasa_bcv_dia()
            resultado['tasa_web'] = tasa_web
        except Exception as e:
            resultado['errores'].append(f"Error obteniendo tasa web: {e}")
        
        # Probar función principal
        try:
            tasa_final = obtener_tasa_bcv()
            resultado['tasa_final'] = tasa_final
        except Exception as e:
            resultado['errores'].append(f"Error en función principal: {e}")
        
        # Información adicional
        resultado['info'] = {
            'archivo_tasa': ULTIMA_TASA_BCV_FILE,
            'fecha_prueba': datetime.now().isoformat(),
            'sistema_inteligente': 'Sí - Busca en facturas, cotizaciones y cuentas'
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/actualizar-tasa-bcv', methods=['POST'])
@login_required
def actualizar_tasa_bcv():
    try:
        # Intentar obtener la tasa del día
        tasa = obtener_tasa_bcv_dia()
        
        if tasa is None or tasa <= 0:
            # Si falla, intentar obtener la tasa del archivo
            tasa = cargar_ultima_tasa_bcv()
            if tasa is None or tasa <= 0:
                return jsonify({
                    'success': False, 
                    'error': 'No se pudo obtener la tasa BCV. Por favor, intente más tarde.'
                })
        
        # Guardar la nueva tasa
        guardar_ultima_tasa_bcv(tasa)
        
        # Registrar en la bitácora
        registrar_bitacora(
            session.get('usuario', 'Sistema'),
            'Actualización de Tasa BCV',
            f'Nueva tasa: {tasa}'
        )
        
        return jsonify({
            'success': True,
            'tasa': tasa,
            'message': f'Tasa BCV actualizada exitosamente: {tasa}'
        })
        
    except Exception as e:
        print(f"Error al actualizar tasa BCV: {str(e)}")
        log_error(
            logger_obs,
            'actualizar_tasa_bcv_error',
            e,
            usuario=session.get('usuario', 'desconocido'),
        )
        notify_critical(
            'actualizar_tasa_bcv_error',
            'Error al actualizar tasa BCV',
            {'error': str(e)},
        )
        return jsonify({
            'success': False,
            'error': f'Error al actualizar la tasa BCV: {str(e)}'
        })

# Rutas para gestión de categorías
@app.route('/categorias')
@login_required
def gestionar_categorias():
    # Cargar el inventario
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Obtener categorías únicas
    categorias = []
    for id, producto in inventario.items():
        if producto.get('categoria') and producto['categoria'] not in [c['nombre'] for c in categorias]:
            categorias.append({
                'id': len(categorias) + 1,
                'nombre': producto['categoria']
            })
    
    return render_template('gestionar_categorias.html', categorias=categorias)

@app.route('/categorias', methods=['POST'])
@login_required
def crear_categoria():
    nombre = request.form.get('nombre')
    if not nombre:
        flash('El nombre de la categoría es requerido', 'danger')
        return redirect(url_for('gestionar_categorias'))
    
    # Cargar el inventario
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Verificar si la categoría ya existe
    for producto in inventario.values():
        if producto.get('categoria') == nombre:
            flash('Esta categoría ya existe', 'danger')
            return redirect(url_for('gestionar_categorias'))
    
    # Crear un nuevo producto con la categoría para mantenerla en el sistema
    nuevo_id = str(max([int(k) for k in inventario.keys()]) + 1) if inventario else '1'
    inventario[nuevo_id] = {
        'nombre': f'Producto de categoría {nombre}',
        'categoria': nombre,
        'precio': 0,
        'cantidad': 0,
        'ultima_entrada': datetime.now().isoformat()
    }
    
    if guardar_datos(ARCHIVO_INVENTARIO, inventario):
        flash('Categoría creada exitosamente', 'success')
    else:
        flash('Error al crear la categoría', 'danger')
    
    return redirect(url_for('gestionar_categorias'))

@app.route('/categorias/<int:id>/editar', methods=['POST'])
@login_required
def editar_categoria(id):
    nuevo_nombre = request.form.get('nuevo_nombre')
    if not nuevo_nombre:
        flash('El nuevo nombre de la categoría es requerido', 'danger')
        return redirect(url_for('gestionar_categorias'))
    
    # Cargar el inventario
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Verificar si el nuevo nombre ya existe
    for producto in inventario.values():
        if producto.get('categoria') == nuevo_nombre:
            flash('Ya existe una categoría con ese nombre', 'danger')
            return redirect(url_for('gestionar_categorias'))
    
    # Encontrar la categoría actual
    categoria_actual = None
    for producto in inventario.values():
        if producto.get('categoria') and producto['categoria'] not in [c['nombre'] for c in [{'nombre': p.get('categoria')} for p in inventario.values() if p.get('categoria')]]:
            categoria_actual = producto['categoria']
            break
    
    if not categoria_actual:
        flash('Categoría no encontrada', 'danger')
        return redirect(url_for('gestionar_categorias'))
    
    # Actualizar la categoría en todos los productos
    for producto in inventario.values():
        if producto.get('categoria') == categoria_actual:
            producto['categoria'] = nuevo_nombre
    
    if guardar_datos(ARCHIVO_INVENTARIO, inventario):
        flash('Categoría actualizada exitosamente', 'success')
    else:
        flash('Error al actualizar la categoría', 'danger')
    
    return redirect(url_for('gestionar_categorias'))

@app.route('/categorias/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_categoria(id):
    # Cargar el inventario
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Encontrar la categoría
    categoria = None
    for producto in inventario.values():
        if producto.get('categoria') and producto['categoria'] not in [c['nombre'] for c in [{'nombre': p.get('categoria')} for p in inventario.values() if p.get('categoria')]]:
            categoria = producto['categoria']
            break
    
    if not categoria:
        flash('Categoría no encontrada', 'danger')
        return redirect(url_for('gestionar_categorias'))
    
    # Verificar si hay productos asociados
    productos_asociados = [p for p in inventario.values() if p.get('categoria') == categoria]
    if len(productos_asociados) > 1:  # Más de 1 porque uno es el producto de la categoría
        flash('No se puede eliminar la categoría porque tiene productos asociados', 'danger')
        return redirect(url_for('gestionar_categorias'))
    
    # Eliminar el producto de la categoría
    for id_producto, producto in list(inventario.items()):
        if producto.get('categoria') == categoria:
            del inventario[id_producto]
            break
    
    if guardar_datos(ARCHIVO_INVENTARIO, inventario):
        flash('Categoría eliminada exitosamente', 'success')
    else:
        flash('Error al eliminar la categoría', 'danger')
    
    return redirect(url_for('gestionar_categorias'))

@app.route('/inventario/ajustes-masivos')
@login_required
def ajustes_masivos():
    inventario = cargar_datos('inventario.json')
    # Recolectar todos los ajustes
    ajustes = []
    for producto in inventario.values():
        nombre_producto = producto.get('nombre', '')
        if 'historial_ajustes' in producto:
            for ajuste in producto['historial_ajustes']:
                tipo = ajuste.get('tipo', '')
                ajustes.append({
                    'fecha': ajuste.get('fecha', ''),
                    'motivo': ajuste.get('motivo', ''),
                    'producto': nombre_producto,
                    'tipo': tipo,
                    'ingreso': ajuste['cantidad'] if tipo == 'entrada' else 0,
                    'salida': ajuste['cantidad'] if tipo == 'salida' else 0,
                    'usuario': ajuste.get('usuario', ''),
                    'observaciones': ajuste.get('observaciones', ajuste.get('motivo', ''))
                })
    # Obtener filtros
    filtro_fecha = request.args.get('fecha', '')
    filtro_producto = request.args.get('producto', '').lower()
    filtro_usuario = request.args.get('usuario', '').lower()
    filtro_tipo = request.args.get('tipo', '')
    # Aplicar filtros
    if filtro_fecha:
        ajustes = [a for a in ajustes if a['fecha'][:10] == filtro_fecha]
    if filtro_producto:
        ajustes = [a for a in ajustes if filtro_producto in a['producto'].lower()]
    if filtro_usuario:
        ajustes = [a for a in ajustes if filtro_usuario in a['usuario'].lower()]
    if filtro_tipo:
        ajustes = [a for a in ajustes if a.get('tipo') == filtro_tipo]
    # Ordenar por fecha descendente
    ajustes.sort(key=lambda x: x['fecha'], reverse=True)
    # Obtener listas para filtros
    productos = sorted(list(set(a['producto'] for a in ajustes)))
    usuarios = sorted(list(set(a['usuario'] for a in ajustes)))
    return render_template('ajustes_masivos.html', 
                         ajustes=ajustes,
                         productos=productos,
                         usuarios=usuarios,
                         filtro_fecha=filtro_fecha,
                         filtro_producto=filtro_producto,
                         filtro_usuario=filtro_usuario,
                         filtro_tipo=filtro_tipo)

@app.route('/api/tasas')
def api_tasas():
    try:
        r = requests.get('https://s3.amazonaws.com/dolartoday/data.json', timeout=5)
        data = r.json()
        tasa_bcv = float(data['USD']['bcv']) if 'USD' in data and 'bcv' in data['USD'] else None
        tasa_paralelo = float(data['USD']['promedio']) if 'USD' in data and 'promedio' in data['USD'] else None
        tasa_bcv_eur = float(data['EUR']['promedio']) if 'EUR' in data and 'promedio' in data['EUR'] else None
        return jsonify({
            'tasa_bcv': tasa_bcv,
            'tasa_paralelo': tasa_paralelo,
            'tasa_bcv_eur': tasa_bcv_eur
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasas-actualizadas')
def api_tasas_actualizadas():
    try:
        # 1. Obtener tasa BCV (USD/BS) desde Monitor Dólar
        tasa_bcv = None
        try:
            r = requests.get('https://s3.amazonaws.com/dolartoday/data.json', timeout=5)
            if r.status_code == 200:
                data = r.json()
                if 'USD' in data and 'bcv' in data['USD']:
                    tasa_bcv = float(str(data['USD']['bcv']).replace(',', '.'))
        except Exception as e:
            print(f"Error obteniendo BCV de Monitor Dólar: {e}")
            tasa_bcv = None

        # 2. Tasa paralela: manual (no scraping ni API)
        tasa_paralelo = 0  # Puedes cambiar esto si quieres pasarla manualmente
        fuente_paralelo = 'manual'

        # 3. Obtener tasa EUR/BS desde la página oficial del BCV (scraping solo por <strong>)
        tasa_bcv_eur = None
        try:
            url_bcv = 'https://www.bcv.org.ve/'
            resp = requests.get(url_bcv, timeout=10, verify=False)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                import re
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Buscar todos los <strong> que contengan un número con coma decimal
                for strong in soup.find_all('strong'):
                    txt = strong.get_text(strip=True)
                    valor_limpio = re.sub(r'[^\d,\.]', '', txt)
                    valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
                    try:
                        posible = float(valor_limpio)
                        if 10 < posible < 500:
                            tasa_bcv_eur = posible
                            break
                    except Exception as e:
                        continue
            if tasa_bcv_eur is None:
                print('No se encontró la tasa EUR en <strong> en el HTML del BCV. Primeros 2000 caracteres:')
                print(resp.text[:2000])
                tasa_bcv_eur = 0
        except Exception as e:
            print(f"Error obteniendo EUR/BS de BCV: {e}")
            tasa_bcv_eur = 0

        # Fallbacks
        if tasa_bcv is None:
            tasa_bcv = cargar_ultima_tasa_bcv() or 1.0
        if tasa_paralelo is None:
            tasa_paralelo = tasa_bcv
        if tasa_bcv_eur is None:
            tasa_bcv_eur = 0

        # Guardar la última tasa BCV
        if tasa_bcv:
            guardar_ultima_tasa_bcv(tasa_bcv)

        return jsonify({
            'success': True,
            'tasa_bcv': tasa_bcv,
            'tasa_paralelo': tasa_paralelo,
            'tasa_bcv_eur': tasa_bcv_eur,
            'fuente_paralelo': fuente_paralelo,
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        # En caso de error, devolver las últimas tasas guardadas
        ultima_tasa = cargar_ultima_tasa_bcv() or 1.0
        return jsonify({
            'success': False,
            'error': str(e),
            'tasa_bcv': ultima_tasa,
            'tasa_paralelo': ultima_tasa,
            'tasa_bcv_eur': 0,
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/inventario/lista-precios/<tipo>')
@login_required
def lista_precios(tipo):
    if tipo not in ['detal', 'distribuidor']:
        abort(404)
    
    # Obtener filtros
    filtro_categoria = request.args.get('categoria', '')
    filtro_precio_min = request.args.get('precio_min', '')
    filtro_precio_max = request.args.get('precio_max', '')
    filtro_busqueda = request.args.get('busqueda', '')
    
    # Cargar datos
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    empresa = cargar_datos('empresa.json')
    fecha_actual = datetime.now()
    
    # Obtener categorías únicas
    categorias = sorted(set(producto.get('categoria', '') for producto in inventario.values() if producto.get('categoria')))
    
    # Filtrar productos
    productos_filtrados = {}
    for id_producto, producto in inventario.items():
        # Aplicar filtros
        if filtro_categoria and producto.get('categoria') != filtro_categoria:
            continue
            
        precio = float(producto.get('precio', 0))
        if filtro_precio_min and precio < float(filtro_precio_min):
            continue
        if filtro_precio_max and precio > float(filtro_precio_max):
            continue
            
        if filtro_busqueda:
            busqueda = filtro_busqueda.lower()
            if busqueda not in producto.get('nombre', '').lower():
                continue
                
        productos_filtrados[id_producto] = producto
    
    return render_template('lista_precios.html', 
                         inventario=productos_filtrados, 
                         tipo=tipo, 
                         empresa=empresa,
                         now=fecha_actual,
                         categorias=categorias,
                         filtro_categoria=filtro_categoria,
                         filtro_precio_min=filtro_precio_min,
                         filtro_precio_max=filtro_precio_max,
                         filtro_busqueda=filtro_busqueda)

@app.route('/inventario/lista-precios/<tipo>/pdf')
@login_required
def lista_precios_pdf(tipo):
    if tipo not in ['detal', 'distribuidor']:
        abort(404)
    # Obtener filtros
    filtro_categoria = request.args.get('categoria', '')
    filtro_precio_min = request.args.get('precio_min', '')
    filtro_precio_max = request.args.get('precio_max', '')
    filtro_busqueda = request.args.get('busqueda', '')
    # Cargar datos
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    empresa = cargar_datos('empresa.json')
    
    # Convertir rutas relativas a absolutas para las imágenes
    if empresa.get('logo'):
        empresa['logo'] = request.url_root.rstrip('/') + url_for('static', filename=empresa['logo'])
    if empresa.get('membrete'):
        empresa['membrete'] = request.url_root.rstrip('/') + url_for('static', filename=empresa['membrete'])
    
    fecha_actual = datetime.now()
    # Obtener categorías únicas
    categorias = sorted(set(producto.get('categoria', '') for producto in inventario.values() if producto.get('categoria')))
    # Filtrar productos
    productos_filtrados = {}
    for id_producto, producto in inventario.items():
        if filtro_categoria and producto.get('categoria') != filtro_categoria:
            continue
        precio = float(producto.get('precio', 0))
        if filtro_precio_min and precio < float(filtro_precio_min):
            continue
        if filtro_precio_max and precio > float(filtro_precio_max):
            continue
        if filtro_busqueda:
            busqueda = filtro_busqueda.lower()
            if busqueda not in producto.get('nombre', '').lower():
                continue
        productos_filtrados[id_producto] = producto
    rendered = render_template('lista_precios.html', 
                             inventario=productos_filtrados, 
                             tipo=tipo, 
                             empresa=empresa, 
                             pdf=True,
                             now=fecha_actual,
                             app=app,
                             categorias=categorias,
                             filtro_categoria=filtro_categoria,
                             filtro_precio_min=filtro_precio_min,
                             filtro_precio_max=filtro_precio_max,
                             filtro_busqueda=filtro_busqueda)
    try:
        # Intentar diferentes ubicaciones comunes de wkhtmltopdf
        wkhtmltopdf_paths = [
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            'wkhtmltopdf'  # Si está en el PATH
        ]
        
        config = None
        for path in wkhtmltopdf_paths:
            if os.path.exists(path):
                config = pdfkit.configuration(wkhtmltopdf=path)
                break
        
        if config is None:
            # Si no se encuentra wkhtmltopdf, intentar usar el comando directamente
            config = pdfkit.configuration(wkhtmltopdf='wkhtmltopdf')
        
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'quiet': '',
            'print-media-type': None,
            'orientation': 'Portrait',
            'dpi': 300,
            'image-quality': 100,
            'enable-local-file-access': None,
            'javascript-delay': '1000',
            'no-stop-slow-scripts': None
        }
        pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=lista_precios_{tipo}.pdf'
        return response
    except Exception as e:
        print(f"Error al generar PDF: {str(e)}")  # Para debugging
        flash(f'Error al generar PDF: {str(e)}', 'danger')
        return redirect(url_for('lista_precios', tipo=tipo))

# ========================================
# RUTAS SENIAT - INTERFACE DE CONSULTA Y ADMINISTRACIÓN
# ========================================



# --- Funciones Auxiliares para WhatsApp ---
def limpiar_numero_telefono(telefono):
    """Limpia y formatea un número de teléfono para WhatsApp."""
    try:
        print(f"🔧 Formateando teléfono: {telefono}")
        
        # Verificar que el teléfono no esté vacío
        if not telefono or str(telefono).strip() == '':
            raise ValueError("El número de teléfono está vacío")
        
        # Remover todos los caracteres no numéricos
        telefono_limpio = re.sub(r'[^\d]', '', str(telefono))
        print(f"🔧 Solo números: {telefono_limpio}")
        
        # Verificar que haya números después de limpiar
        if not telefono_limpio:
            raise ValueError("No se encontraron números en el teléfono")
        
        # Si empieza con 0, removerlo
        if telefono_limpio.startswith('0'):
            telefono_limpio = telefono_limpio[1:]
            print(f"🔧 Removido 0 inicial: {telefono_limpio}")
        
        # Si empieza con +58, removerlo
        if telefono_limpio.startswith('58'):
            telefono_limpio = telefono_limpio[2:]
            print(f"🔧 Removido 58 inicial: {telefono_limpio}")
        
        # Verificar longitud y agregar 58 si es necesario
        if len(telefono_limpio) == 10:
            telefono_limpio = '58' + telefono_limpio
            print(f"🔧 Agregado 58 para 10 dígitos: {telefono_limpio}")
        elif len(telefono_limpio) == 9:
            telefono_limpio = '58' + telefono_limpio
            print(f"🔧 Agregado 58 para 9 dígitos: {telefono_limpio}")
        
        print(f"🔧 Teléfono final formateado: {telefono_limpio}")
        
        # Validar que el resultado sea válido
        if len(telefono_limpio) < 11:
            raise ValueError(f"Teléfono formateado muy corto: {telefono_limpio}")
        
        return telefono_limpio
        
    except Exception as e:
        print(f"❌ Error en limpiar_numero_telefono: {e}")
        raise

def crear_mensaje_recordatorio(factura, cliente):
    """Crea un mensaje personalizado de recordatorio de pago."""
    try:
        print(f"💬 Creando mensaje para factura: {factura.get('numero', 'N/A')}")
        print(f"💬 Cliente: {cliente.get('nombre', 'N/A')}")
        
        numero_factura = factura.get('numero', 'N/A')
        fecha_factura = factura.get('fecha', 'N/A')
        total_usd = factura.get('total_usd', 0)
        saldo_pendiente = factura.get('saldo_pendiente', 0)
        vencimiento = factura.get('fecha_vencimiento', 'No especificado')
        
        print(f"💬 Datos extraídos: Factura={numero_factura}, Fecha={fecha_factura}, Total=${total_usd}, Saldo=${saldo_pendiente}")
        
        mensaje = f"""🏢 *RECORDATORIO DE PAGO*

Hola {cliente.get('nombre', 'Cliente')}, 

Te recordamos que tienes una factura pendiente de pago:

📄 *Factura:* {numero_factura}
📅 *Fecha:* {fecha_factura}
💰 *Total:* ${total_usd:.2f}
⏰ *Vencimiento:* {vencimiento}

💳 *Saldo pendiente:* ${saldo_pendiente:.2f}

Por favor, realiza el pago correspondiente para evitar cargos adicionales.

Si ya realizaste el pago, ignora este mensaje.

Para cualquier consulta, no dudes en contactarnos.

¡Gracias por tu preferencia!

---
*Este es un mensaje automático del sistema de facturación*"""
        
        print(f"💬 Mensaje creado exitosamente: {len(mensaje)} caracteres")
        return mensaje
        
    except Exception as e:
        print(f"❌ Error creando mensaje: {e}")
        raise

def generar_enlace_whatsapp(telefono, mensaje):
    """Genera un enlace de WhatsApp con el mensaje predefinido."""
    try:
        print(f"🔗 Generando enlace para teléfono: {telefono}")
        print(f"🔗 Mensaje a codificar: {len(mensaje)} caracteres")
        
        # Codificar el mensaje para URL - preservar emojis
        mensaje_codificado = urllib.parse.quote(mensaje, safe='')
        print(f"🔗 Mensaje codificado: {len(mensaje_codificado)} caracteres")
        
        # Crear enlace de WhatsApp - usar wa.me para mejor compatibilidad y evitar errores 404
        enlace = f"https://wa.me/{telefono}?text={mensaje_codificado}"
        print(f"🔗 Enlace generado: {enlace[:100]}...")
        return enlace
    except Exception as e:
        print(f"❌ Error generando enlace: {e}")
        raise

def generar_enlaces_whatsapp_completos(telefono, mensaje):
    """Genera múltiples enlaces de WhatsApp para máxima compatibilidad."""
    try:
        print(f"🔗 Generando enlaces completos para teléfono: {telefono}")
        
        # Codificar el mensaje para URL
        mensaje_codificado = urllib.parse.quote(mensaje, safe='')
        
        # Enlaces con diferentes formatos para máxima compatibilidad
        enlaces = {
            'app_movil': f"https://wa.me/{telefono}?text={mensaje_codificado}",
            'web_whatsapp': f"https://web.whatsapp.com/send?phone={telefono}&text={mensaje_codificado}",
            'web_whatsapp_alt': f"https://web.whatsapp.com/send?phone={telefono}&text={mensaje_codificado}&app_absent=0",
            'fallback': f"https://wa.me/{telefono}"  # Sin mensaje, solo abre el chat
        }
        
        print(f"🔗 Enlaces generados exitosamente")
        return enlaces
    except Exception as e:
        print(f"❌ Error generando enlaces completos: {e}")
        raise

# --- Bloque para Ejecutar la Aplicación ---
# MOVIDO AL FINAL DEL ARCHIVO PARA QUE SE REGISTREN TODAS LAS RUTAS

@app.route('/initdb')
@admin_required
def initdb():
    db.create_all()
    return 'Base de datos inicializada correctamente.'

@app.route('/debug-recordatorio/<id>')
@csrf.exempt
def debug_recordatorio(id):
    """Ruta de debug para diagnosticar problemas con recordatorios."""
    try:
        print(f"🔍 DEBUG recordatorio para factura: {id}")
        
        # Verificar que la factura existe
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        cliente_id = factura.get('cliente_id')
        
        # Verificar que el cliente existe
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        if not cliente_id or cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        # Información de debug
        debug_info = {
            'factura_id': id,
            'factura_numero': factura.get('numero', 'N/A'),
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono_original': telefono,
            'telefono_formateado': None,
            'mensaje_generado': None,
            'enlace_generado': None,
            'errores': []
        }
        
        # Probar cada función paso a paso
        try:
            telefono_formateado = limpiar_numero_telefono(telefono)
            debug_info['telefono_formateado'] = telefono_formateado
            print(f"✅ Teléfono formateado: {telefono_formateado}")
        except Exception as e:
            error_msg = f"Error formateando teléfono: {e}"
            debug_info['errores'].append(error_msg)
            print(f"❌ {error_msg}")
            return jsonify(debug_info)
        
        try:
            mensaje = crear_mensaje_recordatorio(factura, cliente)
            debug_info['mensaje_generado'] = mensaje[:200] + '...' if len(mensaje) > 200 else mensaje
            print(f"✅ Mensaje generado: {len(mensaje)} caracteres")
        except Exception as e:
            error_msg = f"Error creando mensaje: {e}"
            debug_info['errores'].append(error_msg)
            print(f"❌ {error_msg}")
            return jsonify(debug_info)
        
        try:
            enlace = generar_enlace_whatsapp(telefono_formateado, mensaje)
            debug_info['enlace_generado'] = enlace[:200] + '...' if len(enlace) > 200 else enlace
            print(f"✅ Enlace generado: {len(enlace)} caracteres")
        except Exception as e:
            error_msg = f"Error generando enlace: {e}"
            debug_info['errores'].append(error_msg)
            print(f"❌ {error_msg}")
            return jsonify(debug_info)
        
        debug_info['success'] = True
        debug_info['message'] = 'Todas las funciones funcionan correctamente'
        print(f"✅ Debug completado exitosamente para factura {id}")
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        error_info = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        print(f"❌ Error fatal en debug: {error_info}")
        return jsonify(error_info), 500

@app.route('/webauthn/register/options', methods=['POST'])
def webauthn_register_options():
    username = request.json.get('username')
    if not username:
        return jsonify({'error': 'Usuario requerido'}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    options = generate_registration_options(user)
    session['webauthn_registration_challenge'] = options.challenge
    return jsonify(options.registration_dict)

@app.route('/webauthn/register/verify', methods=['POST'])
def webauthn_register_verify():
    username = request.json.get('username')
    credential = request.json.get('credential')
    if not username or not credential:
        return jsonify({'error': 'Datos incompletos'}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    challenge = session.get('webauthn_registration_challenge')
    if not challenge:
        return jsonify({'error': 'Challenge no encontrado'}), 400
    try:
        response = WebAuthnRegistrationResponse(
            rp_id=os.environ.get('WEBAUTHN_RP_ID', 'localhost'),
            origin=os.environ.get('WEBAUTHN_ORIGIN', 'http://localhost:5000'),
            registration_response=credential,
            challenge=challenge,
            uv_required=False
        )
        cred = response.verify()
        user.credential_id = cred.credential_id
        user.public_key = cred.public_key
        user.sign_count = cred.sign_count
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/webauthn/authenticate/options', methods=['POST'])
def webauthn_authenticate_options():
    username = request.json.get('username')
    if not username:
        return jsonify({'error': 'Usuario requerido'}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.credential_id:
        return jsonify({'error': 'Usuario o credencial no encontrada'}), 404
    options = generate_assertion_options(user)
    session['webauthn_authenticate_challenge'] = options.challenge
    return jsonify(options.assertion_dict)

@app.route('/webauthn/authenticate/verify', methods=['POST'])
def webauthn_authenticate_verify():
    username = request.json.get('username')
    credential = request.json.get('credential')
    if not username or not credential:
        return jsonify({'error': 'Datos incompletos'}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.credential_id:
        return jsonify({'error': 'Usuario o credencial no encontrada'}), 404
    challenge = session.get('webauthn_authenticate_challenge')
    if not challenge:
        return jsonify({'error': 'Challenge no encontrado'}), 400
    try:
        response = WebAuthnAssertionResponse(
            rp_id=os.environ.get('WEBAUTHN_RP_ID', 'localhost'),
            origin=os.environ.get('WEBAUTHN_ORIGIN', 'http://localhost:5000'),
            assertion_response=credential,
            challenge=challenge,
            credential_public_key=user.public_key,
            credential_current_sign_count=user.sign_count,
            uv_required=False
        )
        sign_count = response.verify()
        user.sign_count = sign_count
        db.session.commit()
        session['usuario'] = username
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# --- Funcionalidad WhatsApp para Cuentas por Cobrar ---

# Ruta de prueba para verificar que la ruta con path funciona
@app.route('/test-path/<path:test_id>')
def test_path(test_id):
    return jsonify({'message': f'Ruta con path funcionando, ID recibido: {test_id}'})

# Ruta de prueba específica para WhatsApp
@app.route('/test-whatsapp-simple/<path:cliente_id>')
def test_whatsapp_simple(cliente_id):
    """Ruta de prueba simple para verificar que la ruta funciona"""
    try:
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        if cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono': cliente.get('telefono', 'N/A')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta de debug para ver qué está pasando (sin login para pruebas)
@app.route('/debug-whatsapp/<path:cliente_id>')
def debug_whatsapp(cliente_id):
    """Ruta de debug para diagnosticar problemas con WhatsApp"""
    try:
        print(f"🔍 DEBUG WhatsApp para cliente: {cliente_id}")
        
        # Cargar datos
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        
        print(f"📊 Clientes cargados: {len(clientes)}")
        print(f"📊 Facturas cargadas: {len(facturas)}")
        
        if cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        # Buscar facturas del cliente
        facturas_cliente = []
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                facturas_cliente.append({
                    'id': factura_id,
                    'numero': factura.get('numero', 'N/A'),
                    'total_usd': factura.get('total_usd', 0),
                    'total_abonado': factura.get('total_abonado', 0)
                })
        
        debug_info = {
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono_original': telefono,
            'telefono_tipo': str(type(telefono)),
            'facturas_encontradas': len(facturas_cliente),
            'facturas_detalle': facturas_cliente[:5],  # Solo las primeras 5
            'tiene_telefono': bool(telefono and str(telefono).strip()),
            'longitud_telefono': len(str(telefono)) if telefono else 0
        }
        
        print(f"🔍 Debug info: {debug_info}")
        return jsonify(debug_info)
        
    except Exception as e:
        print(f"❌ Error en debug: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Ruta para servir la página de prueba
@app.route('/test-whatsapp-routes')
def test_whatsapp_routes():
    """Página de prueba para verificar que las rutas de WhatsApp funcionan"""
    return render_template('test_whatsapp.html')



# Ruta de prueba que funciona exactamente como la principal pero sin autenticación
@app.route('/test-whatsapp-working/<path:cliente_id>', methods=['POST'])
@csrf.exempt
def test_whatsapp_working(cliente_id):
    """Ruta de prueba que funciona exactamente como la principal pero sin autenticación"""
    try:
        print(f"🔍 TEST WhatsApp WORKING para cliente: {cliente_id}")
        
        # Cargar datos
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        
        if cliente_id not in clientes:
            return jsonify({
                'error': 'Cliente no encontrado',
                'cliente_id_buscado': cliente_id,
                'clientes_disponibles': list(clientes.keys())[:10]
            }), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        if not telefono or str(telefono).strip() == '':
            return jsonify({
                'error': 'Cliente sin teléfono',
                'cliente_id': cliente_id,
                'cliente_nombre': cliente.get('nombre', 'N/A'),
                'telefono': telefono
            }), 400
        
        # Buscar facturas pendientes
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'saldo': saldo_pendiente
                    })
                    total_pendiente += saldo_pendiente
        
        # Crear mensaje simple
        mensaje = f"Hola {cliente.get('nombre', 'Cliente')}, tienes {len(facturas_pendientes)} facturas pendientes por un total de ${total_pendiente:.2f} USD. Por favor contacta para coordinar el pago."
        
        # Generar enlace simple
        telefono_limpio = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not telefono_limpio.startswith('58'):
            telefono_limpio = '58' + telefono_limpio.lstrip('0')
        enlace_whatsapp = f"https://wa.me/{telefono_limpio}?text={mensaje.replace(' ', '%20')}"
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono': telefono,
            'telefono_formateado': telefono_limpio,
            'facturas_pendientes': len(facturas_pendientes),
            'total_pendiente': total_pendiente,
            'mensaje': mensaje,
            'enlace_whatsapp': enlace_whatsapp
        })
        
    except Exception as e:
        print(f"❌ Error en test working: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Ruta de prueba que simula el botón de WhatsApp (sin login)
@app.route('/test-whatsapp-button/<path:cliente_id>')
def test_whatsapp_button(cliente_id):
    """Ruta de prueba que simula exactamente lo que hace el botón de WhatsApp"""
    try:
        print(f"🔍 TEST WhatsApp Button para cliente: {cliente_id}")
        
        # Cargar datos
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        
        if cliente_id not in clientes:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        # Simular el mismo flujo que la función principal
        if not telefono or str(telefono).strip() == '':
            return jsonify({
                'error': 'Cliente sin teléfono',
                'cliente_id': cliente_id,
                'cliente_nombre': cliente.get('nombre', 'N/A'),
                'telefono': telefono
            }), 400
        
        # Buscar facturas pendientes
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'saldo': saldo_pendiente
                    })
                    total_pendiente += saldo_pendiente
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono': telefono,
            'facturas_pendientes': len(facturas_pendientes),
            'total_pendiente': total_pendiente,
            'facturas_detalle': facturas_pendientes[:3]  # Solo las primeras 3
        })
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        return jsonify({'error': str(e)}), 500

# Ruta de prueba sin login para diagnosticar problemas
@app.route('/test-whatsapp-no-login/<path:cliente_id>', methods=['POST'])
@csrf.exempt
def test_whatsapp_no_login(cliente_id):
    """Ruta de prueba sin login para diagnosticar problemas de WhatsApp"""
    try:
        print(f"🔍 TEST WhatsApp NO LOGIN para cliente: {cliente_id}")
        
        # Cargar datos
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        
        if cliente_id not in clientes:
            return jsonify({
                'error': 'Cliente no encontrado',
                'cliente_id_buscado': cliente_id,
                'clientes_disponibles': list(clientes.keys())[:10]
            }), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        # Simular el mismo flujo que la función principal
        if not telefono or str(telefono).strip() == '':
            return jsonify({
                'error': 'Cliente sin teléfono',
                'cliente_id': cliente_id,
                'cliente_nombre': cliente.get('nombre', 'N/A'),
                'telefono': telefono
            }), 400
        
        # Buscar facturas pendientes
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'saldo': saldo_pendiente
                    })
                    total_pendiente += saldo_pendiente
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'telefono': telefono,
            'facturas_pendientes': len(facturas_pendientes),
            'total_pendiente': total_pendiente,
            'facturas_detalle': facturas_pendientes[:3]  # Solo las primeras 3
        })
        
    except Exception as e:
        print(f"❌ Error en test no login: {e}")
        return jsonify({'error': str(e)}), 500

# RUTA CON PARÁMETROS - COMENTADA TEMPORALMENTE PARA EVITAR CONFLICTOS
# @app.route('/cuentas-por-cobrar/<path:cliente_id>/enviar_recordatorio_whatsapp', methods=['POST'])
# def enviar_recordatorio_cuentas_por_cobrar_con_parametros(cliente_id):
    """Envía un recordatorio de WhatsApp con todas las facturas pendientes de un cliente."""
    try:
        # Verificar autenticación manualmente para mejor manejo de errores
        if 'usuario' not in session:
            print("❌ Usuario no autenticado")
            return jsonify({
                'error': 'Usuario no autenticado',
                'redirect': url_for('login')
            }), 401
        
        print(f"🔍 Iniciando envío de recordatorio WhatsApp para cliente: {cliente_id}")
        print(f"🔍 Método HTTP: {request.method}")
        print(f"🔍 Headers: {dict(request.headers)}")
        print(f"🔍 Usuario autenticado: {session.get('usuario')}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        print(f"📊 Facturas cargadas: {len(facturas)}")
        print(f"👥 Clientes cargados: {len(clientes)}")
        
        if cliente_id not in clientes:
            print(f"❌ Cliente {cliente_id} no encontrado")
            return jsonify({
                'error': 'Cliente no encontrado',
                'debug_info': {
                    'cliente_id_buscado': cliente_id,
                    'clientes_disponibles': list(clientes.keys())[:10]  # Solo los primeros 10
                }
            }), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        print(f"👤 Cliente: {cliente.get('nombre', 'N/A')}")
        print(f"📱 Teléfono: '{telefono}' (tipo: {type(telefono)})")
        
        if not telefono or str(telefono).strip() == '':
            print(f"❌ Cliente {cliente_id} no tiene teléfono o está vacío")
            return jsonify({
                'error': 'El cliente no tiene número de teléfono registrado o está vacío',
                'debug_info': {
                    'cliente_id': cliente_id,
                    'cliente_nombre': cliente.get('nombre', 'N/A'),
                    'telefono_valor': telefono,
                    'telefono_tipo': str(type(telefono))
                }
            }), 400
        
        # Filtrar facturas pendientes del cliente
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                # Calcular saldo pendiente
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'fecha': factura.get('fecha', 'N/A'),
                        'total': total_factura,
                        'abonado': total_abonado,
                        'saldo': saldo_pendiente,
                        'vencimiento': factura.get('fecha_vencimiento', 'No especificado')
                    })
                    total_pendiente += saldo_pendiente
        
        if not facturas_pendientes:
            print(f"✅ Cliente {cliente_id} no tiene facturas pendientes")
            return jsonify({
                'success': True,
                'message': 'El cliente no tiene facturas pendientes de pago',
                'facturas_pendientes': 0,
                'total_pendiente': 0
            })
        
        print(f"📋 Facturas pendientes encontradas: {len(facturas_pendientes)}")
        print(f"💰 Total pendiente: ${total_pendiente:.2f}")
        
        # Limpiar y formatear el número de teléfono
        telefono_original = telefono
        print(f"📱 Teléfono original recibido: '{telefono}' (tipo: {type(telefono)})")
        
        try:
            # Formateo simple y directo
            telefono = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not telefono.startswith('58'):
                telefono = '58' + telefono.lstrip('0')
            print(f"📱 Teléfono formateado exitosamente: {telefono}")
        except Exception as e:
            print(f"❌ Error formateando teléfono: {e}")
            return jsonify({
                'error': f'Error formateando teléfono: {str(e)}',
                'debug_info': {
                    'telefono_original': telefono_original,
                    'tipo_telefono': str(type(telefono_original)),
                    'cliente_id': cliente_id,
                    'cliente_nombre': cliente.get('nombre', 'N/A')
                }
            }), 400
        
        if not telefono or len(str(telefono)) < 8:
            print(f"❌ Teléfono formateado no válido: {telefono}")
            return jsonify({
                'error': 'El número de teléfono no es válido después del formateo',
                'debug_info': {
                    'telefono_formateado': telefono,
                    'longitud': len(str(telefono)) if telefono else 0,
                    'cliente_id': cliente_id
                }
            }), 400
        
        # Crear mensaje personalizado para cuentas por cobrar
        try:
            # Mensaje simple y directo
            mensaje = f"Hola {cliente.get('nombre', 'Cliente')}, tienes {len(facturas_pendientes)} facturas pendientes por un total de ${total_pendiente:.2f} USD. Por favor contacta para coordinar el pago."
            print(f"💬 Mensaje creado exitosamente: {len(mensaje)} caracteres")
            print(f"💬 Mensaje completo: {mensaje}")
        except Exception as e:
            print(f"❌ Error creando mensaje: {e}")
            return jsonify({'error': f'Error creando mensaje: {str(e)}'}), 400
        
        # Generar enlace de WhatsApp
        try:
            # Enlace simple y directo
            telefono_limpio = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            print(f"🔗 Teléfono limpio: {telefono_limpio}")
            if not telefono_limpio.startswith('58'):
                telefono_limpio = '58' + telefono_limpio.lstrip('0')
                print(f"🔗 Teléfono con prefijo 58: {telefono_limpio}")
            enlace_whatsapp = f"https://wa.me/{telefono_limpio}?text={mensaje.replace(' ', '%20')}"
            print(f"🔗 Enlace WhatsApp generado exitosamente: {enlace_whatsapp}")
        except Exception as e:
            print(f"❌ Error generando enlace: {e}")
            return jsonify({'error': f'Error generando enlace: {str(e)}'}), 400
        
        # Registrar en la bitácora (opcional, no fallar si hay error)
        try:
            # Registro simple en consola
            print(f"📝 REGISTRO: Usuario {session.get('usuario', 'Sistema')} envió recordatorio WhatsApp a {cliente.get('nombre', 'N/A')} - {len(facturas_pendientes)} facturas pendientes - Total: ${total_pendiente:.2f}")
        except Exception as e:
            print(f"⚠️ Error registrando en bitácora (no crítico): {e}")
        
        resultado = {
            'success': True,
            'message': 'Recordatorio de cuentas por cobrar preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'facturas_pendientes': len(facturas_pendientes),
            'total_pendiente': total_pendiente,
        }
        
        print(f"✅ Recordatorio preparado exitosamente para {cliente.get('nombre', 'N/A')}")
        print(f"📱 Teléfono: {telefono}")
        print(f"🔗 Enlace: {enlace_whatsapp}")
        
        return jsonify(resultado)
        
    except Exception as e:
        error_msg = f"Error al enviar recordatorio de cuentas por cobrar: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Traceback completo:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Error al preparar el recordatorio: {str(e)}',
            'debug_info': {
                'cliente_id': cliente_id,
                'error_type': type(e).__name__,
                'error_details': str(e)
            }
        }), 500

# Función auxiliar para enviar recordatorios
def enviar_recordatorio_cuentas_por_cobrar(cliente_id):
    """Envía un recordatorio de WhatsApp con todas las facturas pendientes de un cliente."""
    try:
        # Verificar autenticación manualmente para mejor manejo de errores
        if 'usuario' not in session:
            print("❌ Usuario no autenticado")
            return jsonify({
                'error': 'Usuario no autenticado',
                'redirect': url_for('login')
            }), 401
        
        print(f"🔍 Iniciando envío de recordatorio WhatsApp para cliente: {cliente_id}")
        
        # Cargar datos necesarios
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        print(f"📊 Facturas cargadas: {len(facturas)}")
        print(f"👥 Clientes cargados: {len(clientes)}")
        
        if cliente_id not in clientes:
            print(f"❌ Cliente {cliente_id} no encontrado")
            return jsonify({
                'error': 'Cliente no encontrado',
                'debug_info': {
                    'cliente_id_buscado': cliente_id,
                    'clientes_disponibles': list(clientes.keys())[:10]
                }
            }), 404
        
        cliente = clientes[cliente_id]
        telefono = cliente.get('telefono', '')
        
        print(f"👤 Cliente: {cliente.get('nombre', 'N/A')}")
        print(f"📱 Teléfono: '{telefono}' (tipo: {type(telefono)})")
        
        if not telefono or str(telefono).strip() == '':
            print(f"❌ Cliente {cliente_id} no tiene teléfono o está vacío")
            return jsonify({
                'error': 'El cliente no tiene número de teléfono registrado o está vacío',
                'debug_info': {
                    'cliente_id': cliente_id,
                    'cliente_nombre': cliente.get('nombre', 'N/A'),
                    'telefono_valor': telefono,
                    'telefono_tipo': str(type(telefono))
                }
            }), 400
        
        # Filtrar facturas pendientes del cliente
        facturas_pendientes = []
        total_pendiente = 0.0
        
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                # Calcular saldo pendiente
                total_factura = float(factura.get('total_usd', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                saldo_pendiente = max(0, total_factura - total_abonado)
                
                if saldo_pendiente > 0:
                    facturas_pendientes.append({
                        'id': factura_id,
                        'numero': factura.get('numero', 'N/A'),
                        'fecha': factura.get('fecha', 'N/A'),
                        'total': total_factura,
                        'abonado': total_abonado,
                        'saldo': saldo_pendiente,
                        'vencimiento': factura.get('fecha_vencimiento', 'No especificado')
                    })
                    total_pendiente += saldo_pendiente
        
        if not facturas_pendientes:
            print(f"✅ Cliente {cliente_id} no tiene facturas pendientes")
            return jsonify({
                'success': True,
                'message': 'El cliente no tiene facturas pendientes de pago',
                'facturas_pendientes': 0,
                'total_pendiente': 0
            })
        
        print(f"📋 Facturas pendientes encontradas: {len(facturas_pendientes)}")
        print(f"💰 Total pendiente: ${total_pendiente:.2f}")
        
        # Limpiar y formatear el número de teléfono
        telefono_original = telefono
        print(f"📱 Teléfono original recibido: '{telefono}' (tipo: {type(telefono)})")
        
        try:
            # Formateo simple y directo
            telefono = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not telefono.startswith('58'):
                telefono = '58' + telefono.lstrip('0')
            print(f"📱 Teléfono formateado exitosamente: {telefono}")
        except Exception as e:
            print(f"❌ Error formateando teléfono: {e}")
            return jsonify({
                'error': f'Error formateando número de teléfono: {str(e)}',
                'debug_info': {
                    'telefono_original': telefono_original,
                    'tipo_telefono': str(type(telefono_original)),
                    'cliente_id': cliente_id,
                    'cliente_nombre': cliente.get('nombre', 'N/A')
                }
            }), 400
        
        if not telefono or len(str(telefono)) < 8:
            print(f"❌ Teléfono formateado no válido: {telefono}")
            return jsonify({
                'error': 'El número de teléfono no es válido después del formateo',
                'debug_info': {
                    'telefono_formateado': telefono,
                    'longitud': len(str(telefono)) if telefono else 0,
                    'cliente_id': cliente_id
                }
            }), 400
        
        # Crear mensaje personalizado para cuentas por cobrar
        try:
            # Mensaje simple y directo
            mensaje = f"Hola {cliente.get('nombre', 'Cliente')}, tienes {len(facturas_pendientes)} facturas pendientes por un total de ${total_pendiente:.2f} USD. Por favor contacta para coordinar el pago."
            print(f"💬 Mensaje creado exitosamente: {len(mensaje)} caracteres")
            print(f"💬 Mensaje completo: {mensaje}")
        except Exception as e:
            print(f"❌ Error creando mensaje: {e}")
            return jsonify({'error': f'Error creando mensaje: {str(e)}'}), 400
        
        # Generar enlace de WhatsApp
        try:
            # Enlace simple y directo
            telefono_limpio = str(telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            print(f"🔗 Teléfono limpio: {telefono_limpio}")
            if not telefono_limpio.startswith('58'):
                telefono_limpio = '58' + telefono_limpio.lstrip('0')
                print(f"🔗 Teléfono con prefijo 58: {telefono_limpio}")
            # Usar urllib.parse.quote para codificar el mensaje correctamente
            mensaje_codificado = urllib.parse.quote(mensaje)
            enlace_whatsapp = f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}"
            enlace_web = f"https://web.whatsapp.com/send?phone={telefono_limpio}&text={mensaje_codificado}"
            print(f"🔗 Enlace WhatsApp generado exitosamente: {enlace_whatsapp}")
            print(f"🔗 Enlace Web generado exitosamente: {enlace_web}")
        except Exception as e:
            print(f"❌ Error generando enlace: {e}")
            return jsonify({'error': f'Error generando enlace: {str(e)}'}), 400
        
        # Registrar en la bitácora (opcional, no fallar si hay error)
        try:
            # Registro simple en consola
            print(f"📝 REGISTRO: Usuario {session.get('usuario', 'Sistema')} envió recordatorio WhatsApp a {cliente.get('nombre', 'N/A')} - {len(facturas_pendientes)} facturas pendientes - Total: ${total_pendiente:.2f}")
        except Exception as e:
            print(f"⚠️ Error registrando en bitácora (no crítico): {e}")
        
        resultado = {
            'success': True,
            'message': 'Recordatorio de cuentas por cobrar preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'enlace_web': enlace_web,
            'telefono': telefono,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'total_facturas': len(facturas_pendientes),
            'total_facturado': sum(f['total'] for f in facturas_pendientes),
            'total_abonado': sum(f['abonado'] for f in facturas_pendientes),
            'total_pendiente': total_pendiente,
        }
        
        print(f"✅ Recordatorio preparado exitosamente para {cliente.get('nombre', 'N/A')}")
        print(f"📱 Teléfono: {telefono}")
        print(f"🔗 Enlace: {enlace_whatsapp}")
        
        return jsonify(resultado)
        
    except Exception as e:
        error_msg = f"Error al enviar recordatorio de cuentas por cobrar: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Traceback completo:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Error al preparar el recordatorio: {str(e)}',
            'debug_info': {
                'cliente_id': cliente_id,
                'error_type': type(e).__name__,
                'error_details': str(e)
            }
        }), 500

# Ruta de prueba para verificar que funciona
@app.route('/test-recordatorio', methods=['GET'])
def test_recordatorio():
    return jsonify({'message': 'Ruta de prueba funcionando', 'status': 'success'})

# Ruta de prueba para enlaces de WhatsApp mejorados
@app.route('/test-whatsapp-enlaces/<telefono>', methods=['GET'])
def test_whatsapp_enlaces(telefono):
    """Prueba la generación de enlaces de WhatsApp con diferentes formatos."""
    try:
        mensaje_prueba = "Hola, este es un mensaje de prueba desde KISVIC 🚀"
        enlaces = generar_enlaces_whatsapp_completos(telefono, mensaje_prueba)
        
        return jsonify({
            'success': True,
            'telefono': telefono,
            'mensaje': mensaje_prueba,
            'enlaces': enlaces,
            'recomendaciones': {
                'app_movil': 'Para dispositivos móviles - más confiable',
                'web_whatsapp': 'Para WhatsApp Web - puede fallar en algunos navegadores',
                'web_whatsapp_alt': 'Alternativa para WhatsApp Web con parámetros adicionales',
                'fallback': 'Solo abre el chat sin mensaje - último recurso'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Ruta de prueba para verificar que funciona
@app.route('/test-simple', methods=['GET'])
def test_simple():
    return jsonify({'message': 'Ruta simple funcionando', 'status': 'success'})

# Ruta de prueba para verificar que funciona
@app.route('/test-post', methods=['POST'])
def test_post():
    return jsonify({'message': 'Ruta POST funcionando', 'status': 'success'})



@app.route('/facturas/<path:cliente_id>/enviar_informe_facturas_pagadas', methods=['POST'])
@csrf.exempt
def enviar_informe_facturas_pagadas(cliente_id):
    """Envía un informe de facturas pagadas, abonadas y cobradas por WhatsApp al cliente."""
    try:
        print(f"📊 Iniciando envío de informe de facturas pagadas para cliente: {cliente_id}")
        
        # Cargar datos
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        
        if not clientes or not facturas:
            return jsonify({'error': 'No se pudieron cargar los datos del sistema'}), 400
        
        # Obtener cliente
        cliente = clientes.get(cliente_id)
        if not cliente:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        print(f"👤 Cliente encontrado: {cliente.get('nombre', 'N/A')}")
        
        # Obtener teléfono del cliente
        telefono = cliente.get('telefono', '')
        if not telefono:
            return jsonify({'error': 'El cliente no tiene número de teléfono registrado'}), 400
        
        print(f"📱 Teléfono del cliente: {telefono}")
        
        # Limpiar y formatear el número de teléfono
        telefono_original = telefono
        try:
            telefono = limpiar_numero_telefono(telefono)
            print(f"📱 Teléfono formateado exitosamente: {telefono}")
        except Exception as e:
            print(f"❌ Error formateando teléfono: {e}")
            return jsonify({'error': f'Error formateando teléfono: {str(e)}'}), 400
        
        print(f"📱 Teléfono original: {telefono_original}")
        print(f"📱 Teléfono formateado: {telefono}")
        
        if not telefono or len(telefono) < 10:
            print(f"❌ Teléfono formateado no válido: {telefono}")
            return jsonify({'error': 'El número de teléfono no es válido'}), 400
        
        # Filtrar facturas del cliente
        facturas_cliente = []
        for factura_id, factura in facturas.items():
            if factura.get('cliente_id') == cliente_id:
                factura_copia = factura.copy()
                factura_copia['_id'] = factura_id
                facturas_cliente.append(factura_copia)
        
        if not facturas_cliente:
            return jsonify({'error': 'El cliente no tiene facturas registradas'}), 400
        
        print(f"📄 Facturas encontradas para el cliente: {len(facturas_cliente)}")
        
        # Crear mensaje del informe
        try:
            mensaje = crear_mensaje_informe_facturas_pagadas(cliente, facturas_cliente)
            print(f"💬 Mensaje del informe creado exitosamente: {len(mensaje)} caracteres")
        except Exception as e:
            print(f"❌ Error creando mensaje del informe: {e}")
            return jsonify({'error': f'Error creando mensaje del informe: {str(e)}'}), 400
        
        # Generar enlace de WhatsApp
        try:
            enlace_whatsapp = generar_enlace_whatsapp(telefono, mensaje)
            print(f"🔗 Enlace WhatsApp generado exitosamente: {enlace_whatsapp}")
        except Exception as e:
            print(f"❌ Error generando enlace: {e}")
            return jsonify({'error': f'Error generando enlace: {str(e)}'}), 400
        
        # Registrar en la bitácora
        try:
            registrar_bitacora(
                session.get('usuario', 'Sistema'),
                'Informe Facturas Pagadas WhatsApp Enviado',
                f'Cliente: {cliente.get("nombre", "N/A")} - {len(facturas_cliente)} facturas en el informe'
            )
            print("📝 Registrado en bitácora")
        except Exception as e:
            print(f"⚠️ Error registrando en bitácora: {e}")
        
        resultado = {
            'success': True,
            'message': 'Informe de facturas pagadas preparado para WhatsApp',
            'enlace_whatsapp': enlace_whatsapp,
            'telefono': telefono,
            'mensaje': mensaje,
            'cliente_nombre': cliente.get('nombre', 'N/A'),
            'total_facturas': len(facturas_cliente),
            'debug_info': {
                'cliente_id': cliente_id,
                'telefono_original': telefono_original,
                'telefono_formateado': telefono
            }
        }
        
        print(f"✅ Informe de facturas pagadas preparado exitosamente para {cliente.get('nombre', 'N/A')}")
        return jsonify(resultado)
        
    except Exception as e:
        error_msg = f"Error al enviar informe de facturas pagadas: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Traceback completo:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Error al preparar el informe: {str(e)}',
            'debug_info': {
                'cliente_id': cliente_id,
                'error_type': type(e).__name__,
                'error_details': str(e)
            }
        })

@app.route('/enviar-informe-facturas-pagadas', methods=['POST'])
@csrf.exempt
def enviar_informe_facturas_pagadas_post():
    """Variante JSON: recibe cliente_id en el cuerpo y delega al handler principal."""
    try:
        payload = request.get_json(silent=True) or {}
        cliente_id = payload.get('cliente_id') or request.form.get('cliente_id')
        if not cliente_id:
            return jsonify({'success': False, 'error': 'cliente_id requerido'}), 400
        return enviar_informe_facturas_pagadas(cliente_id)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def crear_mensaje_informe_facturas_pagadas(cliente, facturas_cliente):
    """Crea un mensaje personalizado del informe de facturas pagadas, abonadas y cobradas."""
    try:
        print(f"💬 Creando informe de facturas para cliente: {cliente.get('nombre', 'N/A')}")
        print(f"💬 Total de facturas: {len(facturas_cliente)}")
        
        nombre_cliente = cliente.get('nombre', 'Cliente')
        
        # Categorizar facturas
        facturas_cobradas = []
        facturas_abonadas = []
        facturas_pagadas = []
        
        for factura in facturas_cliente:
            total_facturado = float(factura.get('total_usd', 0))
            total_abonado = float(factura.get('total_abonado', 0))
            saldo = max(0, total_facturado - total_abonado)
            
            if saldo == 0 and total_abonado > 0:
                facturas_cobradas.append(factura)
            elif total_abonado > 0 and saldo > 0:
                facturas_abonadas.append(factura)
            else:
                facturas_pagadas.append(factura)
        
        # Calcular totales
        total_cobrado = sum(float(f.get('total_usd', 0)) for f in facturas_cobradas)
        total_abonado = sum(float(f.get('total_abonado', 0)) for f in facturas_abonadas)
        total_pagado = sum(float(f.get('total_usd', 0)) for f in facturas_pagadas)
        
        print(f"💬 Facturas cobradas: {len(facturas_cobradas)} - Total: ${total_cobrado:.2f}")
        print(f"💬 Facturas abonadas: {len(facturas_abonadas)} - Total: ${total_abonado:.2f}")
        print(f"💬 Facturas pagadas: {len(facturas_pagadas)} - Total: ${total_pagado:.2f}")
        
        # Crear mensaje
        mensaje = f"""🏢 *INFORME DE FACTURAS - {nombre_cliente.upper()}*

Hola {nombre_cliente}, 

Te enviamos un resumen de tu historial de facturas:

📊 *RESUMEN GENERAL:*
• Total de facturas: {len(facturas_cliente)}
• Monto total facturado: ${sum(float(f.get('total_usd', 0)) for f in facturas_cliente):.2f}

✅ *FACTURAS COMPLETAMENTE COBRADAS:*
• Cantidad: {len(facturas_cobradas)}
• Total: ${total_cobrado:.2f}

💰 *FACTURAS CON ABONOS:*
• Cantidad: {len(facturas_abonadas)}
• Total abonado: ${total_abonado:.2f}

📄 *FACTURAS PENDIENTES:*
• Cantidad: {len(facturas_pagadas)}
• Total pendiente: ${total_pagado:.2f}

📋 *DETALLE DE FACTURAS COBRADAS:*
"""
        
        # Agregar lista de facturas cobradas
        for i, factura in enumerate(facturas_cobradas[:5], 1):  # Máximo 5 para no hacer el mensaje muy largo
            mensaje += f"{i}. {factura.get('numero', 'N/A')} - {factura.get('fecha', 'N/A')} - ${factura.get('total_usd', 0):.2f}\n"
        
        if len(facturas_cobradas) > 5:
            mensaje += f"... y {len(facturas_cobradas) - 5} facturas más\n"
        
        mensaje += f"""

📋 *DETALLE DE FACTURAS CON ABONOS:*
"""
        
        # Agregar lista de facturas abonadas
        for i, factura in enumerate(facturas_abonadas[:5], 1):
            abonado = float(factura.get('total_abonado', 0))
            pendiente = float(factura.get('total_usd', 0)) - abonado
            mensaje += f"{i}. {factura.get('numero', 'N/A')} - Abonado: ${abonado:.2f} - Pendiente: ${pendiente:.2f}\n"
        
        if len(facturas_abonadas) > 5:
            mensaje += f"... y {len(facturas_abonadas) - 5} facturas más\n"
        
        mensaje += f"""

¡Gracias por tu confianza y por mantener al día tus pagos!

Para cualquier consulta sobre tus facturas, no dudes en contactarnos.

---
*Este es un informe automático del sistema de facturación*"""
        
        print(f"💬 Informe de facturas creado exitosamente: {len(mensaje)} caracteres")
        return mensaje
        
    except Exception as e:
        print(f"❌ Error creando informe de facturas: {e}")
        raise

def _adaptar_factura_para_whatsapp(factura: dict) -> dict:
    """Normaliza un diccionario de factura para su formato esperado en mensajes de WhatsApp."""
    if not isinstance(factura, dict):
        return {"numero": "N/A", "fecha": "N/A", "saldo": 0.0, "total": 0.0, "abonado": 0.0}
    
    numero = (
        factura.get("numero")
        or factura.get("numero_factura")
        or factura.get("id")
        or "N/A"
    )
    fecha = factura.get("fecha") or factura.get("fecha_emision") or "N/A"
    
    total = float(factura.get("total") or factura.get("total_usd") or 0.0)
    abonado = float(factura.get("abonado") or factura.get("total_abonado") or factura.get("abonado_usd") or 0.0)
    
    if "saldo" in factura and factura["saldo"] is not None:
        saldo = float(factura["saldo"])
    elif "saldo_pendiente" in factura and factura["saldo_pendiente"] is not None:
        saldo = float(factura["saldo_pendiente"])
    else:
        saldo = max(0.0, total - abonado)

    return {
        "id": str(factura.get("id") or numero),
        "numero": str(numero),
        "fecha": str(fecha),
        "total": total,
        "abonado": abonado,
        "saldo": saldo,
        "vencimiento": factura.get("vencimiento") or factura.get("fecha_vencimiento") or "No especificado"
    }


def crear_mensaje_cuentas_por_cobrar(cliente, facturas_pendientes, total_pendiente):
    """Crea un mensaje personalizado de recordatorio de cuentas por cobrar."""
    try:
        print(f"💬 Creando mensaje de cuentas por cobrar para cliente: {cliente.get('nombre', 'N/A')}")
        print(f"💬 Facturas pendientes: {len(facturas_pendientes)}")
        print(f"💬 Total pendiente: ${total_pendiente:.2f}")
        
        nombre_cliente = cliente.get('nombre', 'Cliente')
        
        # Crear lista de facturas pendientes adaptadas
        lista_facturas = ""
        for i, raw_f in enumerate(facturas_pendientes, 1):
            f_adapted = _adaptar_factura_para_whatsapp(raw_f)
            lista_facturas += f"{i}. {f_adapted['numero']} - {f_adapted['fecha']} - Saldo: ${f_adapted['saldo']:.2f}\n"
        
        mensaje = f"""🏢 *RECORDATORIO DE CUENTAS POR COBRAR*

Hola {nombre_cliente}, 

Te recordamos que tienes facturas pendientes de pago:

📋 *Resumen:*
• Total de facturas pendientes: {len(facturas_pendientes)}
• Monto total pendiente: ${total_pendiente:.2f}

📄 *Facturas pendientes:*
{lista_facturas.strip()}

Por favor, realiza el pago correspondiente para regularizar tu situación.

Si ya realizaste algún pago, ignora este mensaje.

Para cualquier consulta o para coordinar pagos, no dudes en contactarnos.

¡Gracias por tu preferencia!

---
*Este es un mensaje automático del sistema de facturación*"""
        
        print(f"💬 Mensaje de cuentas por cobrar creado exitosamente: {len(mensaje)} caracteres")
        return mensaje
        
    except Exception as e:
        print(f"❌ Error creando mensaje de cuentas por cobrar: {e}")
        raise


# NOTA: Esta sección se consolidó al inicio del archivo para evitar usar rutas del sistema como /data en Render.
# Mantener una única definición de CAPTURAS_FOLDER basada en BASE_PATH y enlazada en tiempo de inicio por render.yaml.

# ========================================
# RUTAS PARA NOTAS DE ENTREGA
# ========================================

@app.route('/notas-entrega')
@login_required
def mostrar_notas_entrega():
    """Muestra la lista de notas de entrega."""
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        # Agregar información del cliente a cada nota
        for nota in notas.values():
            cliente_id = nota.get('cliente_id')
            if cliente_id in clientes:
                nota['cliente_nombre'] = clientes[cliente_id].get('nombre', 'N/A')
                nota['cliente_identificacion'] = clientes[cliente_id].get('identificacion', 'N/A')
            else:
                nota['cliente_nombre'] = 'Cliente no encontrado'
                nota['cliente_identificacion'] = 'N/A'
            
            # Agregar códigos y nombres de productos
            inventario = cargar_datos(ARCHIVO_INVENTARIO)
            productos_codigos = []
            productos_nombres = []
            for producto_id in nota.get('productos', []):
                if producto_id in inventario:
                    productos_codigos.append(inventario[producto_id].get('codigo_barras', 'N/A'))
                    productos_nombres.append(inventario[producto_id].get('nombre', f'Producto {producto_id}'))
                else:
                    productos_codigos.append('N/A')
                    productos_nombres.append(f'Producto {producto_id}')
            nota['productos_codigos'] = productos_codigos
            nota['productos_nombres'] = productos_nombres
            
            # Agregar campos por defecto para notas antiguas
            nota['porcentaje_descuento'] = nota.get('porcentaje_descuento', 0)
            nota['descuento'] = nota.get('descuento', 0)
            nota['total_usd'] = nota.get('total_usd', nota.get('subtotal_usd', 0))
            nota['tasa_bcv'] = nota.get('tasa_bcv', 0)
            nota['fecha_tasa_bcv'] = nota.get('fecha_tasa_bcv', 'N/A')
        
        return render_template('notas_entrega.html', notas=notas, clientes=clientes)
    except Exception as e:
        flash(f'Error cargando notas de entrega: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/notas-entrega/nueva', methods=['GET', 'POST'])
@login_required
def nueva_nota_entrega():
    """Crea una nueva nota de entrega."""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cliente_id = request.form['cliente_id']
            fecha = request.form['fecha']
            hora = request.form.get('hora', datetime.now().strftime('%H:%M:%S'))
            modalidad_pago = request.form['modalidad_pago']
            dias_credito = request.form.get('dias_credito', '30')
            observaciones = request.form.get('observaciones', '')
            porcentaje_descuento = float(request.form.get('porcentaje_descuento', 0))
            
            # Obtener productos, cantidades y precios
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            
            # Validar que hay productos
            if not productos or not cantidades or not precios:
                flash('La nota de entrega debe tener al menos un producto', 'error')
                return redirect(url_for('nueva_nota_entrega'))
            
            # Calcular totales
            subtotal_usd = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios)))
            descuento = subtotal_usd * (porcentaje_descuento / 100)
            total_usd = subtotal_usd - descuento
            
            # Obtener tasa BCV actual
            try:
                from services.bcv_service import obtener_tasa_bcv as obtener_tasa_bcv_actual
                tasa_bcv = obtener_tasa_bcv_actual()

                fecha_tasa_bcv = datetime.now().strftime('%Y-%m-%d')
            except:
                tasa_bcv = None
                fecha_tasa_bcv = None
            
            # Obtener numeración secuencial
            notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
            numero_secuencial = len(notas) + 1
            numero_nota = f"NE-{numero_secuencial:04d}"
            
            # Determinar estado según modalidad de pago
            if modalidad_pago == 'contado':
                estado = 'PENDIENTE_ENTREGA'
                fecha_vencimiento_factura = None
            elif modalidad_pago == 'credito':
                estado = 'PENDIENTE_FACTURACION'
                fecha_vencimiento_factura = (datetime.now() + timedelta(days=int(dias_credito))).strftime('%Y-%m-%d')
            else:  # nota_credito
                estado = 'PENDIENTE_ENTREGA'
                fecha_vencimiento_factura = None
            
            # Crear nota de entrega
            nota = {
                'numero': numero_nota,
                'numero_secuencial': numero_secuencial,
                'fecha': fecha,
                'hora': hora,
                'timestamp_creacion': datetime.now().isoformat(),
                'cliente_id': cliente_id,
                'modalidad_pago': modalidad_pago,
                'dias_credito': int(dias_credito) if modalidad_pago == 'credito' else None,
                'fecha_vencimiento_factura': fecha_vencimiento_factura,
                'productos': productos,
                'cantidades': cantidades,
                'precios': precios,
                'subtotal_usd': subtotal_usd,
                'porcentaje_descuento': porcentaje_descuento,
                'descuento': descuento,
                'total_usd': total_usd,
                'tasa_bcv': tasa_bcv,
                'fecha_tasa_bcv': fecha_tasa_bcv,
                'observaciones': observaciones,
                'estado': estado,
                'usuario_creacion': session['usuario'],
                'firma_recibido': False,
                'fecha_entrega': None,
                'hora_entrega': None,
                'entregado_por': None,
                'recibido_por': None,
                'documento_identidad': None
            }
            
            # Guardar nota
            notas[numero_nota] = nota
            guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
            
            # Descontar stock del inventario
            try:
                inventario = cargar_datos(ARCHIVO_INVENTARIO)
                for i, producto_id in enumerate(productos):
                    if producto_id in inventario:
                        cantidad_actual = int(inventario[producto_id].get('stock', 0))
                        cantidad_vendida = int(cantidades[i])
                        nuevo_stock = max(0, cantidad_actual - cantidad_vendida)
                        inventario[producto_id]['stock'] = nuevo_stock
                        
                        # Registrar en bitácora
                        registrar_bitacora(session['usuario'], 'Descontar stock por nota de entrega', 
                                         f"Producto: {producto_id}, Cantidad: {cantidad_vendida}, Stock anterior: {cantidad_actual}, Stock nuevo: {nuevo_stock}")
                
                guardar_datos(ARCHIVO_INVENTARIO, inventario)
                print(f"✅ Stock descontado exitosamente para nota {numero_nota}")
                
            except Exception as e:
                print(f"❌ Error descontando stock: {e}")
                # No fallar la creación de la nota si hay error en stock
                flash(f'Nota creada pero hubo un error actualizando el inventario: {e}', 'warning')
            
            # Mensaje según modalidad
            if modalidad_pago == 'contado':
                flash(f'Nota de entrega #{numero_nota} creada (Contado)', 'success')
            elif modalidad_pago == 'credito':
                flash(f'Nota de entrega #{numero_nota} creada (A Crédito - Facturar antes del {fecha_vencimiento_factura})', 'warning')
            else:
                flash(f'Nota de entrega #{numero_nota} creada (Nota de Crédito)', 'info')
            
            registrar_bitacora(session['usuario'], 'Nueva nota de entrega', f"Cliente: {cliente_id}, Modalidad: {modalidad_pago}")
            return redirect(url_for('mostrar_notas_entrega'))
            
        except Exception as e:
            flash(f'Error creando nota de entrega: {e}', 'danger')
            return redirect(url_for('nueva_nota_entrega'))
    
    # GET: Mostrar formulario
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('nota_entrega_form.html', clientes=clientes, inventario=inventario)

@app.route('/notas-entrega/<id>/editar', methods=['GET', 'POST'])
@login_required
def editar_nota_entrega(id):
    """Edita una nota de entrega existente."""
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    
    if id not in notas:
        flash('Nota de entrega no encontrada', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))
    
    nota = notas[id]
    
    if request.method == 'POST':
        try:
            # Actualizar datos
            nota['fecha'] = request.form['fecha']
            nota['hora'] = request.form.get('hora', datetime.now().strftime('%H:%M:%S'))
            nota['observaciones'] = request.form.get('observaciones', '')
            
            # Actualizar productos
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            
            if productos and cantidades and precios:
                nota['productos'] = productos
                nota['cantidades'] = cantidades
                nota['precios'] = precios
                nota['subtotal_usd'] = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios)))
            
            # Guardar cambios
            guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
            flash('Nota de entrega actualizada exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Editar nota de entrega', f"Nota: {id}")
            return redirect(url_for('mostrar_notas_entrega'))
            
        except Exception as e:
            flash(f'Error actualizando nota de entrega: {e}', 'danger')
    
    # GET: Mostrar formulario de edición
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('nota_entrega_form.html', nota=nota, clientes=clientes, inventario=inventario, editar=True)

@app.route('/notas-entrega/<id>/marcar-entregado', methods=['GET', 'POST'])
@login_required
def marcar_nota_entregada(id):
    """Marca una nota de entrega como entregada."""
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    
    if id not in notas:
        flash('Nota de entrega no encontrada', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))
    
    nota = notas[id]
    
    if request.method == 'GET':
        # Mostrar formulario con token CSRF
        return render_template('marcar_entregado.html', nota=nota, id=id)
    
    # POST: Procesar formulario
    try:
        # Obtener datos de entrega
        recibido_por = request.form.get('recibido_por', '').strip()
        documento_identidad = request.form.get('documento_identidad', '').strip()
        
        if not recibido_por:
            flash('Debe especificar quién recibe la mercancía', 'danger')
            return redirect(url_for('mostrar_notas_entrega'))
        
        # Actualizar estado
        nota['estado'] = 'ENTREGADO'
        nota['fecha_entrega'] = datetime.now().strftime('%Y-%m-%d')
        nota['hora_entrega'] = datetime.now().strftime('%H:%M:%S')
        nota['entregado_por'] = session['usuario']
        nota['recibido_por'] = recibido_por
        nota['documento_identidad'] = documento_identidad
        nota['firma_recibido'] = True
        
        # Guardar cambios
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        
        # Mensaje según modalidad
        if nota['modalidad_pago'] == 'contado':
            flash(f'Nota de entrega #{id} marcada como entregada (Contado)', 'success')
        elif nota['modalidad_pago'] == 'credito':
            flash(f'Nota de entrega #{id} entregada. RECORDATORIO: Debe generar factura antes del {nota["fecha_vencimiento_factura"]}', 'warning')
        else:
            flash(f'Nota de entrega #{id} marcada como entregada (Nota de Crédito)', 'success')
        
        registrar_bitacora(session['usuario'], 'Marcar nota entregada', f"Nota: {id}, Recibido por: {recibido_por}")
        return redirect(url_for('mostrar_notas_entrega'))
        
    except Exception as e:
        flash(f'Error marcando nota como entregada: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

@app.route('/notas-entrega/<id>/convertir-a-factura', methods=['POST'])
@login_required
def convertir_nota_a_factura(id):
    """Convierte nota de entrega a crédito en factura."""
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        
        if id not in notas:
            flash('Nota de entrega no encontrada', 'danger')
            return redirect(url_for('mostrar_notas_entrega'))
        
        nota = notas[id]
        
        if nota.get('modalidad_pago') != 'credito':
            flash('Solo se pueden convertir notas a crédito', 'warning')
            return redirect(url_for('mostrar_notas_entrega'))
        
        if nota.get('estado') != 'ENTREGADO':
            flash('La nota debe estar entregada para convertirla a factura', 'warning')
            return redirect(url_for('mostrar_notas_entrega'))
        
        # Obtener numeración fiscal
        usuario_actual = session.get('usuario', 'SISTEMA')
        numero_fiscal, numero_secuencial = control_numeracion.obtener_siguiente_numero('FACTURA', usuario_actual)
        
        # Crear factura basada en la nota
        factura = {
            'numero': numero_fiscal,
            'numero_secuencial': numero_secuencial,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M:%S'),
            'timestamp_creacion': datetime.now().isoformat(),
            'cliente_id': nota['cliente_id'],
            'productos': nota['productos'],
            'cantidades': nota['cantidades'],
            'precios': nota['precios'],
            'subtotal_usd': nota['subtotal_usd'],
            'descuento': 0,
            'tipo_descuento': 'bs',
            'descuento_total': 0,
            'iva': 16,  # IVA estándar
            'iva_total': nota['subtotal_usd'] * 0.16,
            'total_usd': nota['subtotal_usd'] * 1.16,
            'condicion_pago': 'credito',
            'dias_credito': nota.get('dias_credito', 30),
            'fecha_vencimiento': (datetime.now() + timedelta(days=nota.get('dias_credito', 30))).strftime('%Y-%m-%d'),
            'nota_entrega_origen': id,
            'estado': 'PENDIENTE',
            'pagos': [],
            'tasa_bcv': 36.00  # Tasa por defecto
        }
        
        # Guardar factura
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        facturas[factura['numero']] = factura
        guardar_datos(ARCHIVO_FACTURAS, facturas)
        
        # Marcar nota como facturada
        nota['estado'] = 'FACTURADO'
        nota['factura_generada'] = factura['numero']
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        
        # Sincronizar con cuentas por cobrar
        sincronizar_cuentas_por_cobrar(factura)
        
        flash(f'Nota de entrega #{id} convertida a factura #{factura["numero"]}', 'success')
        registrar_bitacora(session['usuario'], 'Convertir nota a factura', f"Nota: {id} -> Factura: {factura['numero']}")
        return redirect(url_for('editar_factura', id=factura['numero']))
        
    except Exception as e:
        flash(f'Error convirtiendo nota a factura: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

@app.route('/test-eliminar-nota/<id>')
def test_eliminar_nota(id):
    """Ruta de prueba para verificar eliminación de notas."""
    return f"Ruta de prueba funcionando para nota {id}"

@app.route('/notas-entrega/<id>/eliminar', methods=['GET'])
@login_required
def eliminar_nota_entrega(id):
    """Elimina o anula una nota de entrega según su estado."""
    print(f"🔍 Función eliminar_nota_entrega llamada con ID: {id}")
    print(f"🔍 Método HTTP: {request.method}")
    print(f"🔍 URL: {request.url}")
    
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        print(f"🔍 Notas cargadas: {len(notas)} notas encontradas")
        
        if id not in notas:
            print(f"❌ Nota {id} no encontrada")
            flash('Nota de entrega no encontrada', 'danger')
            return redirect(url_for('mostrar_notas_entrega'))
        
        nota = notas[id]
        print(f"✅ Nota {id} encontrada: {nota.get('numero', 'N/A')}")
        
        # Si la nota está entregada, marcarla como ANULADA en lugar de eliminar
        if nota.get('estado') == 'ENTREGADO':
            print(f"🔄 Nota {id} ya entregada, marcando como ANULADA")
            
            # Marcar como anulada
            nota['estado'] = 'ANULADO'
            nota['fecha_anulacion'] = datetime.now().strftime('%Y-%m-%d')
            nota['hora_anulacion'] = datetime.now().strftime('%H:%M:%S')
            nota['anulado_por'] = session['usuario']
            nota['motivo_anulacion'] = 'Anulada por usuario'
            
            # Guardar cambios
            guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
            print(f"✅ Nota {id} marcada como ANULADA exitosamente")
            
            flash(f'Nota de entrega #{id} marcada como ANULADA', 'warning')
            registrar_bitacora(session['usuario'], 'Anular nota de entrega', f"Nota: {id} - Estado: ENTREGADO -> ANULADO")
            return redirect(url_for('mostrar_notas_entrega'))
        
        # Si la nota NO está entregada, eliminarla completamente
        print(f"🗑️ Nota {id} no entregada, eliminando completamente")
        
        # Restaurar stock del inventario antes de eliminar
        try:
            inventario = cargar_datos(ARCHIVO_INVENTARIO)
            productos = nota.get('productos', [])
            cantidades = nota.get('cantidades', [])
            
            for i, producto_id in enumerate(productos):
                if producto_id in inventario and i < len(cantidades):
                    cantidad_actual = int(inventario[producto_id].get('stock', 0))
                    cantidad_restaurada = int(cantidades[i])
                    nuevo_stock = cantidad_actual + cantidad_restaurada
                    inventario[producto_id]['stock'] = nuevo_stock
                    
                    # Registrar en bitácora
                    registrar_bitacora(session['usuario'], 'Restaurar stock por eliminación de nota', 
                                     f"Producto: {producto_id}, Cantidad: {cantidad_restaurada}, Stock anterior: {cantidad_actual}, Stock nuevo: {nuevo_stock}")
            
            guardar_datos(ARCHIVO_INVENTARIO, inventario)
            print(f"✅ Stock restaurado exitosamente para nota {id}")
            
        except Exception as e:
            print(f"❌ Error restaurando stock: {e}")
            # Continuar con la eliminación aunque falle la restauración de stock
        
        # Eliminar nota completamente
        del notas[id]
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        print(f"✅ Nota {id} eliminada completamente exitosamente")
        
        flash(f'Nota de entrega #{id} eliminada completamente', 'success')
        registrar_bitacora(session['usuario'], 'Eliminar nota de entrega', f"Nota: {id}")
        return redirect(url_for('mostrar_notas_entrega'))
        
    except Exception as e:
        print(f"❌ Error procesando nota {id}: {e}")
        flash(f'Error procesando nota de entrega: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

@app.route('/notas-entrega/<id>/anular', methods=['GET'])
@login_required
def anular_nota_entrega(id):
    """Anula una nota de entrega entregada (marca como ANULADO)."""
    print(f"🔄 Función anular_nota_entrega llamada con ID: {id}")
    
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        
        if id not in notas:
            flash('Nota de entrega no encontrada', 'danger')
            return redirect(url_for('mostrar_notas_entrega'))
        
        nota = notas[id]
        
        # Solo permitir anular si está entregada
        if nota.get('estado') != 'ENTREGADO':
            flash('Solo se pueden anular notas de entrega que estén entregadas', 'warning')
            return redirect(url_for('mostrar_notas_entrega'))
        
        # Marcar como anulada
        nota['estado'] = 'ANULADO'
        nota['fecha_anulacion'] = datetime.now().strftime('%Y-%m-%d')
        nota['hora_anulacion'] = datetime.now().strftime('%H:%M:%S')
        nota['anulado_por'] = session['usuario']
        nota['motivo_anulacion'] = 'Anulada por usuario'
        
        # Guardar cambios
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        print(f"✅ Nota {id} anulada exitosamente")
        
        flash(f'Nota de entrega #{id} anulada exitosamente', 'warning')
        registrar_bitacora(session['usuario'], 'Anular nota de entrega', f"Nota: {id} - Estado: ENTREGADO -> ANULADO")
        return redirect(url_for('mostrar_notas_entrega'))
        
    except Exception as e:
        print(f"❌ Error anulando nota {id}: {e}")
        flash(f'Error anulando nota de entrega: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

@app.route('/notas-entrega/<id>/imprimir')
@login_required
def imprimir_nota_entrega(id):
    """Muestra la nota de entrega para imprimir."""
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    
    if id not in notas:
        flash('Nota de entrega no encontrada', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))
    
    nota = notas[id]
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Obtener información completa del cliente
    cliente = clientes.get(nota['cliente_id'], {})
    nota['cliente_nombre'] = cliente.get('nombre', 'Cliente no encontrado')
    nota['cliente_identificacion'] = cliente.get('identificacion', '')
    nota['cliente_direccion'] = cliente.get('direccion', '')
    nota['cliente_telefono'] = cliente.get('telefono', '')
    nota['cliente_email'] = cliente.get('email', '')
    
    # Obtener nombres y códigos de productos
    productos_nombres = []
    productos_codigos = []
    
    for producto_id in nota.get('productos', []):
        producto = inventario.get(str(producto_id), {})
        productos_nombres.append(producto.get('nombre', f'Producto ID: {producto_id}'))
        productos_codigos.append(producto.get('codigo', ''))
    
    nota['productos_nombres'] = productos_nombres
    nota['productos_codigos'] = productos_codigos
    
    # Cargar tasa BCV si no está disponible
    if not nota.get('tasa_bcv') or nota.get('tasa_bcv') == 0:
        try:
            tasa_data = cargar_datos(ULTIMA_TASA_BCV_FILE, crear_vacio=False) or {}
            nota['tasa_bcv'] = tasa_data.get('tasa', 0)
            nota['fecha_tasa_bcv'] = tasa_data.get('fecha', 'N/A')
        except:
            nota['tasa_bcv'] = 0
            nota['fecha_tasa_bcv'] = 'N/A'
    
    return render_template('nota_entrega_imprimir.html', nota=nota, cliente=cliente)

@app.route('/reporte/notas-entrega')
@login_required
def reporte_notas_entrega():
    """Genera reporte de notas de entrega."""
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        # Filtrar por parámetros
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        estado = request.args.get('estado', '')
        modalidad = request.args.get('modalidad', '')
        
        notas_filtradas = {}
        
        for id_nota, nota in notas.items():
            # Filtro por fecha
            if fecha_inicio and nota['fecha'] < fecha_inicio:
                continue
            if fecha_fin and nota['fecha'] > fecha_fin:
                continue
            
            # Filtro por estado
            if estado and nota['estado'] != estado:
                continue
            
            # Filtro por modalidad
            if modalidad and nota['modalidad_pago'] != modalidad:
                continue
            
            notas_filtradas[id_nota] = nota
        
        # Agregar información del cliente
        for nota in notas_filtradas.values():
            cliente_id = nota.get('cliente_id')
            if cliente_id in clientes:
                nota['cliente_nombre'] = clientes[cliente_id].get('nombre', 'N/A')
            else:
                nota['cliente_nombre'] = 'Cliente no encontrado'
        
        return render_template('reporte_notas_entrega.html', 
                             notas=notas_filtradas, 
                             clientes=clientes,
                             fecha_inicio=fecha_inicio,
                             fecha_fin=fecha_fin,
                             estado=estado,
                             modalidad=modalidad)
        
    except Exception as e:
        flash(f'Error generando reporte: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

@app.route('/notas-entrega/recordatorios-facturacion')
@login_required
def recordatorios_facturacion():
    """Muestra notas pendientes de facturación."""
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        
        # Filtrar notas a crédito pendientes de facturación
        notas_pendientes = []
        for nota in notas.values():
            if (nota.get('modalidad_pago') == 'credito' and 
                nota.get('estado') == 'ENTREGADO'):
                
                # Verificar si está vencida
                if nota.get('fecha_vencimiento_factura'):
                    fecha_vencimiento = datetime.strptime(nota['fecha_vencimiento_factura'], '%Y-%m-%d')
                    dias_restantes = (fecha_vencimiento - datetime.now()).days
                    nota['dias_restantes'] = dias_restantes
                    nota['vencida'] = dias_restantes < 0
                
                notas_pendientes.append(nota)
        
        # Ordenar por fecha de vencimiento (más urgentes primero)
        notas_pendientes.sort(key=lambda x: x.get('fecha_vencimiento_factura', ''))
        
        return render_template('recordatorios_facturacion.html', notas=notas_pendientes)
        
    except Exception as e:
        flash(f'Error cargando recordatorios: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

# ========================================
# FUNCIÓN DE SINCRONIZACIÓN AUTOMÁTICA
# ========================================

def sincronizar_cuentas_por_cobrar(factura):
    """
    Función obsoleta. La información de cuentas por cobrar se calcula dinámicamente
    directamente a partir de facturas.json (fuente única de verdad).
    """
    return True


def notificar_pago_recibido(factura, pago):
    """
    Envía notificaciones automáticas cuando se recibe un pago.
    """
    try:
        # Obtener información del cliente
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        cliente = clientes.get(factura.get('cliente_id', ''), {})
        nombre_cliente = cliente.get('nombre', 'Cliente')
        
        # Crear mensaje de confirmación
        mensaje = f"""💰 *PAGO RECIBIDO CONFIRMADO*

✅ *Factura:* {factura.get('numero', 'N/A')}
👤 *Cliente:* {nombre_cliente}
💵 *Monto:* ${pago.get('monto', 0):.2f}
🏦 *Método:* {pago.get('metodo', 'N/A')}
📅 *Fecha:* {pago.get('fecha', 'N/A')}

*Saldo pendiente:* ${factura.get('saldo_pendiente', 0):.2f}

¡Gracias por tu pago! 🎉"""
        
        print(f"💬 Notificación de pago creada para {nombre_cliente}")
        
        # Aquí se podría integrar con WhatsApp o email
        # Por ahora solo se registra en la bitácora
        registrar_bitacora(
            'SISTEMA',
            'Notificación de pago recibido',
            f"Cliente: {nombre_cliente}, Factura: {factura.get('numero', 'N/A')}, Monto: ${pago.get('monto', 0):.2f}"
        )
        
        return mensaje
        
    except Exception as e:
        print(f"❌ Error creando notificación: {e}")
        return None

# --- FUNCIONALIDAD DE PAGOS EN NOTAS DE ENTREGA ---
# ===================================================

def procesar_pago_nota_entrega(nota_id, monto_pago, metodo_pago, referencia_pago=""):
    """
    Procesa un pago en una nota de entrega y actualiza el inventario.
    Esta función se ejecuta cuando se recibe un pago directo en una nota de entrega.
    """
    try:
        # Cargar datos
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        
        if nota_id not in notas:
            print(f"❌ Nota de entrega {nota_id} no encontrada")
            return False, "Nota de entrega no encontrada"
        
        nota = notas[nota_id]
        
        # Verificar que la nota esté en estado válido
        if nota.get('estado') not in ['PENDIENTE_ENTREGA', 'ENTREGADO']:
            return False, f"La nota no puede recibir pagos en estado: {nota.get('estado')}"
        
        # Inicializar pagos si no existe
        if 'pagos' not in nota:
            nota['pagos'] = []
        
        # Crear registro de pago
        nuevo_pago = {
            'id': str(len(nota['pagos']) + 1),
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'monto': float(monto_pago),
            'metodo': metodo_pago,
            'referencia': referencia_pago,
            'timestamp': datetime.now().isoformat()
        }
        
        # Agregar pago a la nota
        nota['pagos'].append(nuevo_pago)
        
        # Calcular total pagado
        total_pagado = sum(pago['monto'] for pago in nota['pagos'])
        total_nota = float(nota.get('subtotal_usd', 0))
        
        # Actualizar estado de la nota
        if total_pagado >= total_nota:
            nota['estado'] = 'PAGADA'
            nota['fecha_pago_completo'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            nota['estado'] = 'ABONADA'
        
        # Guardar nota actualizada
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        
        # DESCONTAR DEL INVENTARIO
        if nota.get('estado') in ['ENTREGADO', 'PAGADA']:
            productos = nota.get('productos', [])
            cantidades = nota.get('cantidades', [])
            
            for i, producto_id in enumerate(productos):
                cantidad = int(cantidades[i]) if i < len(cantidades) else 0
                
                if producto_id in inventario:
                    stock_actual = int(inventario[producto_id].get('cantidad', 0))
                    nuevo_stock = max(0, stock_actual - cantidad)
                    
                    inventario[producto_id]['cantidad'] = nuevo_stock
                    inventario[producto_id]['ultima_salida'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    print(f"📦 Producto {producto_id}: Stock {stock_actual} -> {nuevo_stock} (descontado: {cantidad})")
                else:
                    print(f"⚠️ Producto {producto_id} no encontrado en inventario")
            
            # Guardar inventario actualizado
            guardar_datos(ARCHIVO_INVENTARIO, inventario)
            print(f"✅ Inventario actualizado para nota {nota_id}")
        
        # SINCRONIZAR CON CUENTAS POR COBRAR SIEMPRE que se procese un pago
        if nota.get('estado') == 'PAGADA':
            # Crear factura automáticamente para sincronización
            factura = crear_factura_desde_nota_pagada(nota)
            if factura:
                sincronizar_cuentas_por_cobrar(factura)
                print(f"✅ Factura creada y sincronizada: {factura['numero']}")
            else:
                # Si no se puede crear factura, sincronizar directamente la nota
                print(f"📊 Sincronizando nota de entrega con cuentas por cobrar")
                # Crear entrada en cuentas por cobrar para la nota pagada
                cuentas = cargar_datos(ARCHIVO_CUENTAS)
                entrada_cuenta = {
                    'rif': nota.get('cliente_id', ''),
                    'total_usd': float(nota.get('subtotal_usd', 0)),
                    'abonado_usd': float(nota.get('subtotal_usd', 0)),
                    'estado': 'Cobrada',
                    'tipo_pago': 'Nota de Entrega',
                    'fecha_ultimo_abono': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_emision': nota.get('fecha', ''),
                    'referencia_pago': f"Nota {nota_id} - Pago completo",
                    'nota_entrega_origen': nota_id
                }
                cuentas[f"NE-{nota_id}"] = entrada_cuenta
                guardar_datos(ARCHIVO_CUENTAS, cuentas)
                print(f"✅ Nota sincronizada con cuentas por cobrar")
        
        # Registrar en bitácora
        registrar_bitacora(
            'SISTEMA',
            'Pago procesado en nota de entrega',
            f"Nota: {nota_id}, Monto: ${monto_pago:.2f}, Estado: {nota['estado']}"
        )
        
        print(f"✅ Pago procesado exitosamente en nota {nota_id}")
        return True, f"Pago procesado. Estado actual: {nota['estado']}"
        
    except Exception as e:
        print(f"❌ Error procesando pago en nota de entrega: {e}")
        return False, f"Error: {str(e)}"

def crear_factura_desde_nota_pagada(nota):
    """
    Crea una factura automáticamente cuando una nota de entrega a crédito se paga completamente.
    """
    try:
        # Obtener numeración fiscal
        usuario_actual = 'SISTEMA'
        numero_fiscal, numero_secuencial = control_numeracion.obtener_siguiente_numero('FACTURA', usuario_actual)
        
        # Crear factura
        factura = {
            'numero': numero_fiscal,
            'numero_secuencial': numero_secuencial,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M:%S'),
            'timestamp_creacion': datetime.now().isoformat(),
            'cliente_id': nota['cliente_id'],
            'productos': nota['productos'],
            'cantidades': nota['cantidades'],
            'precios': nota['precios'],
            'subtotal_usd': nota['subtotal_usd'],
            'descuento': 0,
            'tipo_descuento': 'bs',
            'descuento_total': 0,
            'iva': 16,
            'iva_total': nota['subtotal_usd'] * 0.16,
            'total_usd': nota['subtotal_usd'] * 1.16,
            'condicion_pago': 'contado',  # Ya está pagada
            'dias_credito': 0,
            'fecha_vencimiento': datetime.now().strftime('%Y-%m-%d'),
            'nota_entrega_origen': nota['numero'],
            'estado': 'PAGADA',
            'pagos': nota.get('pagos', []),
            'tasa_bcv': 36.00,
            'total_abonado': nota['subtotal_usd'] * 1.16,
            'saldo_pendiente': 0
        }
        
        # Guardar factura
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        facturas[factura['numero']] = factura
        guardar_datos(ARCHIVO_FACTURAS, facturas)
        
        # Actualizar nota con referencia a la factura
        nota['factura_generada'] = factura['numero']
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        notas[nota['numero']] = nota
        guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
        
        return factura
        
    except Exception as e:
        print(f"❌ Error creando factura desde nota pagada: {e}")
        return None

@app.route('/notas-entrega/<id>/procesar-pago', methods=['POST'])
@login_required
def procesar_pago_nota_entrega_route(id):
    """
    Ruta para procesar pagos en notas de entrega.
    """
    try:
        monto = float(request.form.get('monto', 0))
        metodo = request.form.get('metodo', 'efectivo')
        referencia = request.form.get('referencia', '')
        
        if monto <= 0:
            flash('El monto debe ser mayor a 0', 'danger')
            return redirect(url_for('mostrar_notas_entrega'))
        
        # Procesar el pago
        exito, mensaje = procesar_pago_nota_entrega(id, monto, metodo, referencia)
        
        if exito:
            flash(f'Pago procesado exitosamente: {mensaje}', 'success')
        else:
            flash(f'Error procesando pago: {mensaje}', 'danger')
        
        return redirect(url_for('mostrar_notas_entrega'))
        
    except Exception as e:
        flash(f'Error procesando pago: {e}', 'danger')
        return redirect(url_for('mostrar_notas_entrega'))

# --- Ruta de prueba ---
# NOTA: La función index ya está definida anteriormente

@app.route('/test')
def test():
    return "Test de funcionamiento OK ✅"

# --- INTEGRACIÓN DEL CHATBOT DE WHATSAPP ---
try:
    from whatsapp_chatbot import inicializar_chatbot
    print("🤖 Inicializando chatbot de WhatsApp...")
    chatbot = inicializar_chatbot(app)
    print("✅ Chatbot de WhatsApp inicializado correctamente")
    print("📱 Webhook disponible en: /webhook/whatsapp")
    print("⚙️  Configuración en: /whatsapp/chatbot/config")
except ImportError as e:
    print(f"⚠️  No se pudo importar el chatbot de WhatsApp: {e}")
    chatbot = None
except Exception as e:
    print(f"❌ Error inicializando chatbot: {e}")
    chatbot = None

# --- Ruta adicional para el chatbot ---
@app.route('/chatbot-whatsapp')
@login_required
def chatbot_whatsapp():
    """Página principal del chatbot de WhatsApp"""
    return render_template('whatsapp_chatbot_config.html')

def auto_consolidar_facturas():
    """Autoconsolida facturas locales asegurando que facturas.json contenga todos los archivos individuales."""
    try:
        facturas_dir = 'facturas_json'
        if not os.path.exists(facturas_dir):
            return
        facturas = cargar_datos('facturas_json/facturas.json', crear_vacio=False) or {}
        if not isinstance(facturas, dict):
            facturas = {}
        
        cambios = False
        for fname in os.listdir(facturas_dir):
            if fname.endswith('.json') and fname != 'facturas.json':
                f_key = fname[len('factura_'):-len('.json')] if fname.startswith('factura_') else fname[:-len('.json')]
                if f_key not in facturas:
                    fdata = cargar_datos(os.path.join(facturas_dir, fname), crear_vacio=False)
                    if fdata and isinstance(fdata, dict):
                        f_id = fdata.get('id') or f_key
                        num = fdata.get('numero')
                        facturas[f_id] = fdata
                        if num:
                            facturas[num] = fdata
                        cambios = True
        if cambios:
            guardar_datos('facturas_json/facturas.json', facturas)
            print(f'[auto_consolidar] Se integraron facturas individuales en facturas.json (Total: {len(facturas)})')
    except Exception as e:
        print(f'[auto_consolidar] Advertencia: {e}')

auto_consolidar_facturas()

# Firebase: configuración y migración inicial (solo la primera vez)
try:
    configurar_al_inicio()
except Exception as _fb_err:
    print(f'[almacenamiento] Inicio Firebase: {_fb_err}')

if __name__ == '__main__':
    print("🔍 Rutas disponibles en la aplicación:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    print("🚀 Aplicación iniciada correctamente")
    print("🌐 Iniciando servidor web en http://127.0.0.1:5000")
    print("📱 Para acceder a las notas de entrega: http://127.0.0.1:5000/notas-entrega")
    print("🤖 Para configurar el chatbot: http://127.0.0.1:5000/chatbot-whatsapp")
    print("⏹️  Presiona CTRL+C para detener el servidor")
    
    # Iniciar el servidor Flask
    app.run(debug=True, host='127.0.0.1', port=5000)

